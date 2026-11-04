"""校验并安装已整理的真实语料，复用抽取产物和 P2 图谱格式。"""

import argparse
import hashlib
import json
import sqlite3
import tempfile
import uuid
import zipfile
from collections import defaultdict
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from ..common.config import Settings, fixture_path, get_settings
from ..common.logging import configure_logging, get_logger
from ..common.schemas import MechanismUnit
from ..graph.store import GraphStore
from ..ingest.manifest import write_text
from .pipeline import publish_run

log = get_logger(__name__)


def install_bundle(settings: Settings, archive_path: Path) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        contents = {name: archive.read(name) for name in manifest["files"]}
    for name, expected in manifest["files"].items():
        if hashlib.sha256(contents[name]).hexdigest() != expected:
            raise ValueError("bundle hash mismatch: " + name)
    papers = [json.loads(line) for line in contents["papers.jsonl"].decode().splitlines()]
    by_id = {paper["paper_id"]: paper for paper in papers}
    units = [
        MechanismUnit.model_validate_json(line)
        for line in contents["mechanisms.jsonl"].decode().splitlines()
    ]
    if len(by_id) != len(papers) or len({unit.id for unit in units}) != len(units):
        raise ValueError("duplicate paper or mechanism IDs")
    if len(papers) != manifest["paper_count"] or len(units) != manifest["mechanism_count"]:
        raise ValueError("bundle count mismatch")
    groups = defaultdict(list)
    for unit in units:
        paper = by_id[unit.paper_id]
        evidence = unit.evidence
        if (
            unit.domain != paper["domain"]
            or paper["abstract"][evidence.char_start : evidence.char_end] != evidence.span
        ):
            raise ValueError("mechanism evidence or domain mismatch")
        groups[unit.paper_id].append(unit.model_dump())
    if any(len(group) > 5 for group in groups.values()):
        raise ValueError("more than five mechanisms per paper")
    failures = {
        row["paper_id"]: row
        for row in map(json.loads, contents["failed_papers.jsonl"].decode().splitlines())
    }
    if set(groups) & set(failures) or set(groups) | set(failures) != set(by_id):
        raise ValueError("successful and failed papers must partition the corpus")
    results = [
        {
            "paper_id": paper["paper_id"],
            "ok": paper["paper_id"] in groups,
            "units": groups.get(paper["paper_id"], []),
            "reason": failures.get(paper["paper_id"], {}).get("reason"),
        }
        for paper in papers
    ]
    root = settings.resolved_data_dir
    normalized = root / "normalized"
    normalized.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(normalized / ".extract-lock.sqlite3", timeout=0)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        source = root / "raw/papers.jsonl"
        if source.exists():
            existing = {
                row["paper_id"]: row
                for row in map(json.loads, source.read_text(encoding="utf-8").splitlines())
            }
            if any(existing.get(paper_id) != paper for paper_id, paper in by_id.items()):
                raise ValueError("existing paper source differs from bundle")
        else:
            write_text(source, contents["papers.jsonl"].decode())
        input_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        version = manifest["corpus_version"]
        with tempfile.TemporaryDirectory(prefix="corpus-", dir=root) as temporary:
            graph = Path(temporary) / "graph"
            GraphStore.from_mechanisms(units, version=version).save(graph)
            report = publish_run(
                normalized,
                input_hash,
                papers,
                results,
                {
                    "method": "agent_assisted",
                    "model": manifest["models"],
                    "extractor_version": manifest["extractor_versions"],
                    "corpus_version": version,
                    "source_archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                    "acceptance": manifest["acceptance"],
                    "external_model_api_calls": 0,
                },
                {"task_cache_hits": 0, "first_pass_valid": 0, "imported_papers": len(papers)},
                {"requests": 0, "cache_hits": 0, "gateway_calls": 0},
            )
            index = root / "index"
            index.mkdir(exist_ok=True)
            name = "g-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
            graph.replace(index / name)
        report["installed_index"] = name
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="安装已整理语料及完整图谱，无模型请求")
    parser.add_argument("--archive", type=Path, default=fixture_path("corpus500.zip"))
    args = parser.parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        report = install_bundle(settings, args.archive)
    except (OSError, ValueError, KeyError, sqlite3.Error, zipfile.BadZipFile) as exc:
        log.error("corpus_install_failed", extra={"kv": {"reason": str(exc)}})
        return 1
    log.info("corpus_installed", extra={"kv": report})
    return 0
