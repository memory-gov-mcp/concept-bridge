"""抽取流水线、不可变运行目录及验收报告。"""

import hashlib
import json
import random
import sqlite3
import uuid
from collections import defaultdict
from itertools import zip_longest
from pathlib import Path
from typing import Any

import pandas as pd

from ..common.config import Settings
from ..common.llm import LLMClient
from ..common.schemas import MechanismUnit
from ..ingest.manifest import digest, file_hashes, provenance, write_json, write_text
from .cache import CachedGateway
from .extractor import Extractor
from .normalize import concept


def select_papers(path: Path, limit: int) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("limit must be positive")
    papers = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    seen = set()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for paper in papers:
        for key in ("paper_id", "domain", "abstract"):
            if not isinstance(paper.get(key), str) or not paper[key].strip():
                raise ValueError(f"paper has invalid {key}")
        if paper["paper_id"] in seen:
            raise ValueError("duplicate paper_id in input")
        seen.add(paper["paper_id"])
        groups[paper["domain"]].append(paper)
    if len(papers) < limit:
        raise ValueError(f"requested {limit} papers but only {len(papers)} available")
    ordered = [sorted(groups[domain], key=lambda p: p["paper_id"]) for domain in sorted(groups)]
    return [p for row in zip_longest(*ordered) for p in row if p is not None][:limit]


def concept_rows(units: list[MechanismUnit]) -> tuple[list[dict[str, Any]], int]:
    rows: dict[str, dict[str, Any]] = {}
    originals = set()
    for unit in units:
        for ref in (unit.subject, unit.object):
            originals.add((unit.domain, ref.type, ref.surface))
            _, name = concept(unit.domain, ref.type, ref.surface)
            row = rows.setdefault(
                ref.concept_id,
                {
                    "concept_id": ref.concept_id,
                    "canonical_name": name,
                    "domain": unit.domain,
                    "type": ref.type,
                    "surfaces": [],
                },
            )
            if ref.surface not in row["surfaces"]:
                row["surfaces"].append(ref.surface)
    for row in rows.values():
        row["surfaces"].sort()
    return [rows[key] for key in sorted(rows)], len(originals)


def preview(settings: Settings, limit: int = 8) -> dict[str, Any]:
    papers = select_papers(settings.resolved_data_dir / "raw/papers.jsonl", limit)
    namespace = digest(settings.llm_base_url)[:16]
    gateway = CachedGateway(LLMClient(settings, settings.llm_cache_dir / ("extract-" + namespace)))
    extractor = Extractor(gateway, settings.resolved_data_dir / "normalized/task_cache")
    batches = [papers[offset : offset + 8] for offset in range(0, len(papers), 8)]
    return {
        "papers": len(papers),
        "initial_requests_upper_bound": len(batches),
        "transport_attempts_upper_bound": len(batches) * 3,
        "prompt_characters": sum(
            len(extractor.system) + len(extractor.request_text(batch, {}, 0)) for batch in batches
        ),
        "max_output_tokens_per_request": 8192,
        "retries": 0,
        "model": settings.llm_model,
        "key_configured": bool(settings.llm_api_key),
        "provider_token_usage": "unavailable until provider reports usage",
        "note": "character count is not token count; shared gateway may attempt transport up to 3 times per request",
    }


async def run(
    settings: Settings,
    *,
    limit: int = 8,
    retries: int = 0,
    retry_failed: bool = False,
    gateway: CachedGateway | None = None,
) -> dict[str, Any]:
    root = settings.resolved_data_dir / "normalized"
    root.mkdir(parents=True, exist_ok=True)
    lock = sqlite3.connect(root / ".extract-lock.sqlite3", timeout=0)
    try:
        lock.execute("BEGIN IMMEDIATE")
        source = settings.resolved_data_dir / "raw/papers.jsonl"
        input_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        papers = select_papers(source, limit)
        if gateway is None:
            namespace = digest(settings.llm_base_url)[:16]
            client = LLMClient(settings, settings.llm_cache_dir / ("extract-" + namespace))
            gateway = CachedGateway(client)
        extractor = Extractor(gateway, root / "task_cache")
        results = []
        for offset in range(0, len(papers), 8):
            results.extend(
                await extractor.extract(
                    papers[offset : offset + 8],
                    retries=retries,
                    retry_failed=retry_failed,
                )
            )
        if hashlib.sha256(source.read_bytes()).hexdigest() != input_hash:
            raise ValueError("paper source changed during extraction; cached tasks were preserved")
        return _publish(root, input_hash, papers, results, extractor)
    finally:
        lock.close()


def _publish(root, input_hash, papers, results, extractor) -> dict[str, Any]:
    units = [MechanismUnit.model_validate(item) for result in results for item in result["units"]]
    if len({unit.id for unit in units}) != len(units):
        raise ValueError("duplicate mechanism IDs across papers")
    rows, before = concept_rows(units)
    run_id = "run-" + uuid.uuid4().hex[:16]
    staging = root / "runs" / ("." + run_id)
    staging.mkdir(parents=True)
    write_text(
        staging / "mechanisms.jsonl", "".join(unit.model_dump_json() + "\n" for unit in units)
    )
    columns = ["concept_id", "canonical_name", "domain", "type", "surfaces"]
    pd.DataFrame(rows, columns=columns).to_parquet(staging / "concepts.parquet", index=False)
    failures = [result for result in results if not result["ok"]]
    write_text(
        staging / "failed_papers.jsonl",
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in failures),
    )
    review = random.Random(0).sample(units, min(30, len(units)))
    by_id = {paper["paper_id"]: paper for paper in papers}
    write_json(
        staging / "review_mechanisms.json",
        [
            {
                "mechanism": unit.model_dump(),
                "abstract": by_id[unit.paper_id]["abstract"],
                "correct": None,
                "notes": "",
            }
            for unit in review
        ],
    )
    write_json(
        staging / "review_concepts.json",
        [
            {**row, "correct": None, "notes": ""}
            for row in random.Random(0).sample(rows, min(20, len(rows)))
        ],
    )
    fresh = len(papers) - extractor.stats["task_cache_hits"]
    manifest = {
        **provenance(),
        **extractor.identity,
        "run_id": run_id,
        "paper_count": len(papers),
        "successful_papers": len(papers) - len(failures),
        "failed_papers": len(failures),
        "mechanism_count": len(units),
        "schema_pass_rate": (len(papers) - len(failures)) / len(papers),
        "schema_pass_rate_unit": "papers passing both schema and evidence validation",
        "first_pass_rate": extractor.stats["first_pass_valid"] / fresh if fresh else None,
        "human_accuracy": None,
        "human_review_status": "pending",
        "concepts_before": before,
        "concepts_after": len(rows),
        "input_sha256": input_hash,
        "selected_paper_ids": [p["paper_id"] for p in papers],
        "usage": {**extractor.stats, **extractor.gateway.stats},
        "usage_note": "gateway_calls counts invocations, including failures; provider tokens/cost unavailable",
        "files": file_hashes(staging),
    }
    write_json(staging / "manifest.json", manifest)
    destination = root / "runs" / run_id
    staging.replace(destination)
    # current.json is the authoritative commit marker for multi-file readers.
    write_json(root / "current.json", {"run_id": run_id})
    for name in ("mechanisms.jsonl", "failed_papers.jsonl", "manifest.json"):
        write_text(root / name, (destination / name).read_text(encoding="utf-8"))
    parquet_tmp = root / "concepts.parquet.tmp"
    parquet_tmp.write_bytes((destination / "concepts.parquet").read_bytes())
    parquet_tmp.replace(root / "concepts.parquet")
    return manifest
