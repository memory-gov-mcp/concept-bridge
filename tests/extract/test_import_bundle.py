import hashlib
import json
import zipfile

import pytest

from conceptbridge.common.config import Settings, fixture_path
from conceptbridge.common.schemas import MechanismUnit
from conceptbridge.extract.import_bundle import install_bundle
from conceptbridge.graph.store import GraphStore


def test_expanded_corpus_preserves_pilot_and_evidence():
    with zipfile.ZipFile(fixture_path("corpus500.zip")) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for name, expected in manifest["files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
        papers = {
            row["paper_id"]: row
            for row in map(json.loads, archive.read("papers.jsonl").decode().splitlines())
        }
        units = {
            unit.id: unit
            for unit in map(
                MechanismUnit.model_validate_json,
                archive.read("mechanisms.jsonl").decode().splitlines(),
            )
        }
    assert len(papers) == 500
    assert len(units) == manifest["mechanism_count"] >= 1200
    assert manifest["acceptance"]["human_review_status"] == "pending"
    assert manifest["acceptance"]["original_paper_pass_rate"] == 0.954
    for line in fixture_path("mechanisms.min.jsonl").read_text(encoding="utf-8").splitlines():
        pilot = MechanismUnit.model_validate_json(line)
        assert units[pilot.id] == pilot
    for unit in units.values():
        evidence = unit.evidence
        paper = papers[unit.paper_id]
        assert paper["abstract"][evidence.char_start : evidence.char_end] == evidence.span
        assert unit.domain == paper["domain"]


def test_import_installs_complete_corpus_and_preserves_existing_source(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path, _env_file=None)
    first = install_bundle(settings, fixture_path("corpus500.zip"))
    source = tmp_path / "raw/papers.jsonl"
    extra = {"paper_id": "extra", "domain": "physics", "abstract": "Additional source."}
    source.write_text(source.read_text(encoding="utf-8") + json.dumps(extra) + "\n", encoding="utf-8")
    expected = source.read_bytes()
    second = install_bundle(settings, fixture_path("corpus500.zip"))
    assert source.read_bytes() == expected
    assert first["mechanism_count"] == second["mechanism_count"] >= 1200
    assert first["files"]["mechanisms.jsonl"] == second["files"]["mechanisms.jsonl"]
    assert second["usage"]["gateway_calls"] == 0
    assert second["usage"]["imported_papers"] == 500
    assert second["usage"]["task_cache_hits"] == 0
    assert second["first_pass_rate"] is None
    assert second["human_accuracy"] is None
    assert (tmp_path / "normalized/concepts.parquet").is_file()
    from conceptbridge.match.pipeline import load_corpus

    monkeypatch.setattr("conceptbridge.match.pipeline.get_settings", lambda: settings)
    units, version = load_corpus()
    assert version == second["corpus_version"]
    assert len(units) == second["mechanism_count"]
    assert len(GraphStore.load(tmp_path / "index" / second["installed_index"]).all_mechanisms()) == len(units)


def test_import_rejects_tampering_and_conflicting_source(tmp_path):
    archive_path = tmp_path / "tampered.zip"
    with (
        zipfile.ZipFile(fixture_path("corpus500.zip")) as source,
        zipfile.ZipFile(archive_path, "w") as target,
    ):
        for name in source.namelist():
            data = source.read(name)
            target.writestr(name, data + b" " if name == "mechanisms.jsonl" else data)
    settings = Settings(data_dir=tmp_path / "data", _env_file=None)
    with pytest.raises(ValueError, match="hash mismatch"):
        install_bundle(settings, archive_path)
    assert not settings.resolved_data_dir.exists()
    raw = settings.resolved_data_dir / "raw/papers.jsonl"
    raw.parent.mkdir(parents=True)
    raw.write_text('{"paper_id": "conflict"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="source differs"):
        install_bundle(settings, fixture_path("corpus500.zip"))
    assert not (settings.resolved_data_dir / "normalized/current.json").exists()


def test_formal_mini_bundle_hashes_and_graph():
    root = fixture_path("mini200")
    manifest = json.loads((root / "p1.manifest.json").read_text(encoding="utf-8"))
    assert manifest["paper_count"] == 200
    assert manifest["mechanism_count"] == 500
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
    assert len(GraphStore.load(root / "graph.min").all_mechanisms()) == 500
    assert sum(path.stat().st_size for path in fixture_path("").rglob("*") if path.is_file()) < 5_000_000


def test_matching_reuses_vectors_without_changing_cosine(monkeypatch):
    import numpy as np

    from conceptbridge.graph.embeddings import hash_embed
    from conceptbridge.match import candidate

    calls = []

    def recorded(texts):
        calls.extend(texts)
        return hash_embed(texts)

    candidate._vector.cache_clear()
    monkeypatch.setattr(candidate, "hash_embed", recorded)
    texts = ["ion transport", "膜中的离子传输", "", "lithium dendrite"]
    for left in texts:
        for right in texts:
            vectors = hash_embed([left, right])
            expected = float(np.clip(np.dot(vectors[0], vectors[1]), 0.0, 1.0))
            assert candidate._cosine(left, right) == expected
    assert calls == texts
    candidate._vector.cache_clear()
