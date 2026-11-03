"""采集命令及可恢复的页级快照。"""

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ..common.config import Settings, get_settings
from ..common.logging import configure_logging, get_logger
from .normalize_text import normalize_work
from .openalex import QUERIES, fetch_page

log = get_logger(__name__)


def _atomic_write(path: Path, body: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(body, encoding="utf-8")
    temporary.replace(path)


def _publish(raw: Path, state: dict[str, Any], limit: int) -> dict[str, Any]:
    papers = sorted(state["papers"].values(), key=lambda paper: paper["paper_id"])
    body = "".join(json.dumps(paper, ensure_ascii=False) + "\n" for paper in papers)
    _atomic_write(raw / "papers.jsonl", body)
    _atomic_write(
        raw / "failed_records.jsonl",
        "".join(
            json.dumps(error, ensure_ascii=False) + "\n" for error in state["failures"].values()
        ),
    )
    manifest = {
        "ingestor_version": "ingest-v1",
        "paper_count": len(papers),
        "requested_limit": limit,
        "complete": len(papers) >= limit,
        "domains": dict(Counter(p["domain"] for p in papers)),
        "abstract_nonempty_rate": sum(bool(p["abstract"]) for p in papers) / max(1, len(papers)),
        "domain_missing_rate": sum(not p["domain"] for p in papers) / max(1, len(papers)),
        "failure_count": len(state["failures"]),
        "queries": state["queries"],
        "papers_sha256": hashlib.sha256((raw / "papers.jsonl").read_bytes()).hexdigest(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    _atomic_write(raw / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def collect(
    settings: Settings,
    *,
    limit: int,
    client: httpx.Client,
    queries: tuple[tuple[str, str, str], ...] = QUERIES,
) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("limit must be positive")
    raw = settings.resolved_data_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    # SQLite's OS lock survives stale files and is released if a process crashes.
    lock = sqlite3.connect(raw / ".ingest-lock.sqlite3", timeout=0)
    try:
        lock.execute("BEGIN IMMEDIATE")
        return _collect_locked(settings, raw, limit, client, queries)
    finally:
        lock.close()


def _collect_locked(
    settings: Settings,
    raw: Path,
    limit: int,
    client: httpx.Client,
    queries: tuple[tuple[str, str, str], ...],
) -> dict[str, Any]:
    checkpoint = raw / "checkpoint.json"
    plan = [list(query) for query in queries]
    state: dict[str, Any] = {
        "queries": plan,
        "papers": {},
        "pages": {},
        "pending": {},
        "failures": {},
    }
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text(encoding="utf-8"))
        if state["queries"] != plan:
            raise ValueError("query plan changed; use a separate DATA_DIR")
    elif (raw / "papers.jsonl").exists():
        raise ValueError("papers.jsonl exists without checkpoint; use a separate DATA_DIR")
    # Early cursor checkpoints can restart page traversal safely because IDs are deduplicated.
    state.setdefault("pages", {})
    state.setdefault("pending", {})
    _publish(raw, state, limit)
    for index, (domain, field, query) in enumerate(queries):
        target = limit // len(queries) + int(index < limit % len(queries))
        count = sum(p.get("source_query") == query for p in state["papers"].values())
        page_number = state["pages"].get(query, 1)
        pending = state["pending"].setdefault(query, [])
        while count < target and (pending or page_number is not None):
            if not pending:
                if settings.demo_mode:
                    raise ValueError(
                        "DEMO_MODE requires sufficient cached papers; network disabled"
                    )
                if page_number > 50:
                    raise ValueError("OpenAlex basic paging exhausted; narrow the query")
                params = {
                    "search": query,
                    "filter": f"has_abstract:true,primary_topic.field.id:{field}",
                    "per-page": 200,
                    "page": page_number,
                }
                if settings.openalex_mailto != "team@example.com":
                    params["mailto"] = settings.openalex_mailto
                try:
                    page = fetch_page(client, params)
                except (httpx.HTTPError, ValueError) as exc:
                    error: dict[str, Any] = {"query": query, "reason": type(exc).__name__}
                    if isinstance(exc, httpx.HTTPStatusError):
                        error["status_code"] = exc.response.status_code
                    state["failures"][f"request:{query}"] = error
                    _atomic_write(checkpoint, json.dumps(state, ensure_ascii=False))
                    _publish(raw, state, limit)
                    raise
                pending.extend(page["results"])
                page_number = (
                    page_number + 1
                    if pending and page_number * 200 < page["meta"]["count"]
                    else None
                )
            while pending and count < target:
                work = pending.pop(0)
                try:
                    paper = normalize_work(work)
                except (ValueError, TypeError, AttributeError) as exc:
                    key = str(work.get("id")) if isinstance(work, dict) else repr(work)[:80]
                    state["failures"][key] = {"paper_id": key, "reason": str(exc), "query": query}
                    continue
                if paper["paper_id"] not in state["papers"]:
                    paper["source_query"] = query
                    state["papers"][paper["paper_id"]] = paper
                    count += 1
            state["pages"][query] = page_number
            # Commit accepted papers, unused page records and the next page together.
            _atomic_write(checkpoint, json.dumps(state, ensure_ascii=False))
            _publish(raw, state, limit)
            log.info("page_saved", extra={"kv": {"domain": domain, "papers": count}})
    return _publish(raw, state, limit)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="采集 OpenAlex 论文，自动断点续抓")
    parser.add_argument("--limit", type=int, default=1500)
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit 必须大于 0")
    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            manifest = collect(settings, limit=args.limit, client=client)
    except (OSError, ValueError, sqlite3.Error, httpx.HTTPError) as exc:
        details = {"error": type(exc).__name__}
        if isinstance(exc, httpx.HTTPStatusError):
            details["http_status"] = str(exc.response.status_code)
        elif isinstance(exc, ValueError | sqlite3.Error):
            details["reason"] = str(exc)
        log.error("ingest_failed", extra={"kv": details})
        return 1
    log.info("ingest_complete", extra={"kv": manifest})
    return 0 if manifest["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
