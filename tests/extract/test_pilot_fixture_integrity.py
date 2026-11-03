import hashlib
import json

from conceptbridge.common.config import fixture_path
from conceptbridge.common.schemas import BridgeResult, MechanismUnit
from conceptbridge.graph.store import GraphStore
from conceptbridge.ingest.manifest import digest


def test_real_pilot_papers_mechanisms_and_evidence():
    papers = {
        p["paper_id"]: p
        for p in map(
            json.loads, fixture_path("papers.min.jsonl").read_text(encoding="utf-8").splitlines()
        )
    }
    units = [
        MechanismUnit.model_validate_json(line)
        for line in fixture_path("mechanisms.min.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(papers) == 8
    assert len(units) == len({unit.id for unit in units}) == 17
    assert {unit.paper_id for unit in units} == set(papers)
    assert len({unit.domain for unit in units}) == 6
    for unit in units:
        paper = papers[unit.paper_id]
        evidence = unit.evidence
        assert paper["abstract"][evidence.char_start : evidence.char_end] == evidence.span
        assert unit.domain == paper["domain"]
        assert unit.extractor_version == "curated-codex-v1"
    manifest = json.loads(fixture_path("p1.manifest.json").read_text(encoding="utf-8"))
    drafts = json.loads(fixture_path("pilot8.drafts.json").read_text(encoding="utf-8"))
    assert manifest["extraction"]["draft_sha256"] == digest(drafts)
    assert manifest["extraction"]["external_model_api_calls"] == 0
    for name, expected in manifest["files"].items():
        assert hashlib.sha256(fixture_path(name).read_bytes()).hexdigest() == expected
    loaded = GraphStore.load(fixture_path("graph.min")).all_mechanisms()
    assert {unit.id for unit in loaded} == {unit.id for unit in units}


def test_real_pilot_bridge_sample_is_traceable():
    result = BridgeResult.model_validate_json(
        fixture_path("bridge.pilot8.json").read_text(encoding="utf-8")
    )
    assert result.meta.stub is False
    assert result.meta.degraded is False
    assert len(result.bridges) == 5
    papers = {
        p["paper_id"]: p
        for p in map(
            json.loads, fixture_path("papers.min.jsonl").read_text(encoding="utf-8").splitlines()
        )
    }
    for bridge in result.bridges:
        for citation in bridge.citations:
            assert (
                papers[citation.paper_id]["abstract"][citation.char_start : citation.char_end]
                == citation.span
            )
