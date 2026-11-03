"""验证并发布 P2 可直接加载的迷你图谱。"""

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from itertools import zip_longest
from pathlib import Path

from ..common.config import Settings, fixture_path, get_settings
from ..common.logging import configure_logging, get_logger
from ..common.schemas import MechanismUnit
from ..graph.store import GraphStore
from ..ingest.manifest import file_hashes, provenance, write_json, write_text

log = get_logger(__name__)


def export_bundle(
    settings: Settings,
    output: Path,
    *,
    paper_count: int = 200,
    mechanism_count: int = 500,
    install_index: bool = False,
) -> dict:
    lock_path = settings.resolved_data_dir / "normalized/.extract-lock.sqlite3"
    lock = sqlite3.connect(lock_path, timeout=0)
    try:
        lock.execute("BEGIN IMMEDIATE")
        return _export_locked(
            settings,
            output,
            paper_count=paper_count,
            mechanism_count=mechanism_count,
            install_index=install_index,
        )
    finally:
        lock.close()


def _export_locked(
    settings: Settings,
    output: Path,
    *,
    paper_count: int,
    mechanism_count: int,
    install_index: bool,
) -> dict:
    root = settings.resolved_data_dir
    current = json.loads((root / "normalized/current.json").read_text(encoding="utf-8"))
    run_id = current["run_id"]
    if not re.fullmatch(r"run-[a-f0-9]{16}", run_id):
        raise ValueError("invalid current run_id")
    run_dir = root / "normalized/runs" / run_id
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    source = root / "raw/papers.jsonl"
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["input_sha256"]:
        raise ValueError("paper source changed since extraction")
    mechanisms_file = run_dir / "mechanisms.jsonl"
    if (
        hashlib.sha256(mechanisms_file.read_bytes()).hexdigest()
        != manifest["files"]["mechanisms.jsonl"]
    ):
        raise ValueError("mechanisms hash mismatch")
    papers = {
        p["paper_id"]: p for p in map(json.loads, source.read_text(encoding="utf-8").splitlines())
    }
    by_paper = defaultdict(list)
    for line in mechanisms_file.read_text(encoding="utf-8").splitlines():
        unit = MechanismUnit.model_validate_json(line)
        paper = papers[unit.paper_id]
        evidence = unit.evidence
        if (
            unit.domain != paper["domain"]
            or paper["abstract"][evidence.char_start : evidence.char_end] != evidence.span
        ):
            raise ValueError("mechanism evidence or domain mismatch")
        by_paper[unit.paper_id].append(unit)
    groups = defaultdict(list)
    for paper_id in by_paper:
        groups[papers[paper_id]["domain"]].append(paper_id)
    ordered = [sorted(groups[key], key=lambda p: (-len(by_paper[p]), p)) for key in sorted(groups)]
    selected = [p for row in zip_longest(*ordered) for p in row if p is not None][:paper_count]
    if paper_count < 1 or mechanism_count < paper_count or len(selected) < paper_count:
        raise ValueError("insufficient successful papers or invalid requested counts")
    units = [by_paper[p][0] for p in selected]
    extra = [unit for p in selected for unit in by_paper[p][1:]]
    units.extend(extra[: mechanism_count - len(units)])
    if len(units) != mechanism_count or len({unit.id for unit in units}) != mechanism_count:
        raise ValueError("insufficient distinct mechanisms for selected papers")
    with tempfile.TemporaryDirectory(prefix="fixture-", dir=root) as temporary:
        staging = Path(temporary)
        write_text(
            staging / "papers.min.jsonl",
            "".join(json.dumps(papers[p], ensure_ascii=False) + "\n" for p in selected),
        )
        write_text(
            staging / "mechanisms.min.jsonl", "".join(u.model_dump_json() + "\n" for u in units)
        )
        graph_dir = staging / "graph.min"
        GraphStore.from_mechanisms(units, version=run_id).save(graph_dir)
        graph_manifest = json.loads((graph_dir / "manifest.json").read_text(encoding="utf-8"))
        graph_manifest.update(graph_version=run_id, source_run_id=run_id, embedding="P2 hash_embed")
        write_json(graph_dir / "manifest.json", graph_manifest)
        if [u.id for u in GraphStore.load(graph_dir).all_mechanisms()] != [u.id for u in units]:
            raise ValueError("GraphStore round-trip failed")
        shutil.copyfile(graph_dir / "graph.pkl", staging / "graph.min.pkl")
        report = {
            **provenance(),
            "source_run_id": run_id,
            "paper_count": paper_count,
            "mechanism_count": mechanism_count,
            "embedding": "P2 hash_embed",
            "files": file_hashes(staging),
        }
        write_json(staging / "p1.manifest.json", report)
        # Refuse conflicting bundles. Identical files permit retry after a partial publication.
        for path in staging.rglob("*"):
            target = output / path.relative_to(staging)
            if (
                path.is_file()
                and target.exists()
                and path.name not in ("manifest.json", "p1.manifest.json")
                and target.read_bytes() != path.read_bytes()
            ):
                raise ValueError(
                    "existing fixture bundle differs; choose an empty output directory"
                )
        staged_names = {p.relative_to(staging) for p in staging.rglob("*") if p.is_file()}
        total = sum(p.stat().st_size for p in staging.rglob("*") if p.is_file())
        if output.exists():
            total += sum(
                p.stat().st_size
                for p in output.rglob("*")
                if p.is_file() and p.relative_to(output) not in staged_names
            )
        if total >= 5_000_000:
            raise ValueError("fixtures must total less than 5MB")
        # Publish the manifest last, so consumers can verify all file hashes before use.
        paths = sorted(
            (p for p in staging.rglob("*") if p.is_file()),
            key=lambda p: p.name == "p1.manifest.json",
        )
        for path in paths:
            target = output / path.relative_to(staging)
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            shutil.copyfile(path, tmp)
            tmp.replace(target)
        if install_index:
            index = root / "index"
            index.mkdir(exist_ok=True)
            name = "g-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
            candidate = index / ("." + name)
            shutil.copytree(graph_dir, candidate, ignore=shutil.ignore_patterns("graph.pkl"))
            # load_corpus scans every directory, including hidden staging directories.
            shutil.copyfile(graph_dir / "graph.pkl", candidate / "graph.pending")
            destination = index / name
            candidate.rename(destination)
            (destination / "graph.pending").rename(destination / "graph.pkl")
            report["installed_index"] = name
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导出 200 篇 / 500 机制与 P2 图快照")
    parser.add_argument("--output", type=Path, default=fixture_path(""))
    parser.add_argument("--paper-count", type=int, default=200)
    parser.add_argument("--mechanism-count", type=int, default=500)
    parser.add_argument("--install-index", action="store_true")
    args = parser.parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        report = export_bundle(
            settings,
            args.output,
            paper_count=args.paper_count,
            mechanism_count=args.mechanism_count,
            install_index=args.install_index,
        )
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        log.error("fixture_export_failed", extra={"kv": {"reason": str(exc)}})
        return 1
    log.info("fixture_exported", extra={"kv": report})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
