"""八篇一批抽取，只对失败论文重抽；逐篇缓存已校验结果。"""

import json
from pathlib import Path
from typing import Any

from ..common.schemas import MechanismUnit
from ..ingest.manifest import digest, write_json
from .cache import CachedGateway
from .normalize import NORMALIZER_VERSION
from .validators import EXTRACTOR_VERSION, validate_paper

ROOT = Path(__file__).parent


class Extractor:
    def __init__(self, gateway: CachedGateway, cache_dir: Path) -> None:
        self.gateway, self.cache_dir = gateway, cache_dir
        self.system = (ROOT / "prompts/v1/system.md").read_text(encoding="utf-8")
        self.user = (ROOT / "prompts/v1/user.md").read_text(encoding="utf-8")
        settings = gateway.client.settings
        self.identity = {
            "model": settings.llm_model,
            "provider": settings.llm_base_url,
            "extractor_version": EXTRACTOR_VERSION,
            "normalizer_version": NORMALIZER_VERSION,
            "prompt_hash": digest([self.system, self.user]),
            "code_hash": digest(
                [(p.name, p.read_text(encoding="utf-8")) for p in sorted(ROOT.glob("*.py"))]
            ),
        }
        self.stats = {"papers": 0, "task_cache_hits": 0, "first_pass_valid": 0, "paper_attempts": 0}

    def key(self, paper: dict[str, Any]) -> str:
        return digest([self.identity, paper])

    def request_text(
        self,
        papers: list[dict[str, Any]],
        errors: dict[str, str],
        attempt: int,
        generations: dict[str, int] | None = None,
    ) -> str:
        payload = {
            "papers": [{k: p[k] for k in ("paper_id", "domain", "abstract")} for p in papers],
            "validation_errors": errors,
            "repair_attempt": attempt,
        }
        if generations:
            payload["retry_generations"] = generations
        return self.user + "\n" + json.dumps(payload, ensure_ascii=False)

    async def extract(
        self,
        papers: list[dict[str, Any]],
        *,
        retries: int = 0,
        retry_failed: bool = False,
    ) -> list[dict[str, Any]]:
        if len(papers) > 8 or not 0 <= retries <= 2:
            raise ValueError("batch size must be <=8 and retries must be 0..2")
        self.stats["papers"] += len(papers)
        results: dict[str, dict[str, Any]] = {}
        pending = []
        errors: dict[str, str] = {}
        generations: dict[str, int] = {}
        for paper in papers:
            path = self.cache_dir / (self.key(paper) + ".json")
            if path.exists():
                cached = json.loads(path.read_text(encoding="utf-8"))
                if cached["ok"] or not retry_failed:
                    self._validate_cached(paper, cached)
                    results[paper["paper_id"]] = cached
                    self.stats["task_cache_hits"] += 1
                    continue
                errors[paper["paper_id"]] = cached["reason"]
                generations[paper["paper_id"]] = cached.get("generation", 0) + 1
            pending.append(paper)
        for attempt in range(retries + 1):
            if not pending:
                break
            response = await self.gateway.complete(
                self.system, self.request_text(pending, errors, attempt, generations)
            )
            mapped = self._map_response(response, {p["paper_id"] for p in pending})
            remaining = []
            for paper in pending:
                paper_id = paper["paper_id"]
                self.stats["paper_attempts"] += 1
                try:
                    units = validate_paper(paper, mapped.get(paper_id))
                    result = {
                        "paper_id": paper_id,
                        "ok": True,
                        "attempts": attempt + 1,
                        "units": [unit.model_dump() for unit in units],
                    }
                    if attempt == 0:
                        self.stats["first_pass_valid"] += 1
                except ValueError as exc:
                    # Pydantic errors can contain the source text; keep messages, not input values.
                    message = (
                        exc.errors(include_input=False) if hasattr(exc, "errors") else str(exc)
                    )
                    errors[paper_id] = json.dumps(message, ensure_ascii=False)
                    result = {
                        "paper_id": paper_id,
                        "ok": False,
                        "attempts": attempt + 1,
                        "reason": errors[paper_id],
                        "units": [],
                    }
                    remaining.append(paper)
                results[paper_id] = result
                result["generation"] = generations.get(paper_id, 0)
                write_json(self.cache_dir / (self.key(paper) + ".json"), result)
            pending = remaining
        return [results[p["paper_id"]] for p in papers]

    @staticmethod
    def _map_response(response: dict[str, Any], expected: set[str]) -> dict[str, Any]:
        rows = response.get("papers")
        if not isinstance(rows, list):
            return {}
        mapped = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("paper_id"), str):
                return {}
            if row["paper_id"] not in expected:
                return {}
            if row["paper_id"] in mapped:
                return {}
            mapped[row["paper_id"]] = row.get("mechanisms")
        return mapped

    @staticmethod
    def _validate_cached(paper: dict[str, Any], cached: dict[str, Any]) -> None:
        if cached["paper_id"] != paper["paper_id"]:
            raise ValueError("cached paper mismatch")
        if cached["ok"] and not 1 <= len(cached["units"]) <= 5:
            raise ValueError("cached mechanism count invalid")
        for item in cached["units"]:
            unit = MechanismUnit.model_validate(item)
            evidence = unit.evidence
            if unit.paper_id != paper["paper_id"] or unit.domain != paper["domain"]:
                raise ValueError("cached mechanism identity mismatch")
            if paper["abstract"][evidence.char_start : evidence.char_end] != evidence.span:
                raise ValueError("cached evidence mismatch")
