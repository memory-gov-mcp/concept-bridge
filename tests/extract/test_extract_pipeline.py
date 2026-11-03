import asyncio
import json

import pytest

from conceptbridge.common.config import Settings
from conceptbridge.common.llm import LLMClient
from conceptbridge.extract.cache import CachedGateway
from conceptbridge.extract.export import export_bundle
from conceptbridge.extract.pipeline import run


class FakeClient(LLMClient):
    def __init__(self, settings, *, invalid_first=False, mechanism_count=1):
        super().__init__(settings, settings.resolved_data_dir / "fake_gateway_cache")
        self.calls = 0
        self.invalid_first = invalid_first
        self.mechanism_count = mechanism_count

    async def complete_json(self, **kwargs):
        self.calls += 1
        payload = json.loads(kwargs["user"].split("\n")[-1])
        rows = []
        for paper in payload["papers"]:
            span = "invented" if self.invalid_first and self.calls == 1 else paper["abstract"]
            draft = {
                "subject": {"surface": "membrane", "type": "structure"},
                "action": {"verb": "transport", "action_class": "transport", "polarity": "neutral"},
                "object": {"surface": "ions", "type": "substance"},
                "conditions": ["concentration gradient"],
                "result": "ions move",
                "causality": "direct",
                "evidence": {"span": span},
                "confidence": 0.8,
            }
            drafts = [
                {**draft, "object": {"surface": surface, "type": "substance"}}
                for surface in ("sodium ions", "potassium ions", "chloride ions")[
                    : self.mechanism_count
                ]
            ]
            rows.append({"paper_id": paper["paper_id"], "mechanisms": drafts})
        return {"papers": rows}


def make_settings(tmp_path, count=8):
    settings = Settings(data_dir=tmp_path, llm_api_key="", _env_file=None)
    raw = tmp_path / "raw"
    raw.mkdir()
    rows = [
        {
            "paper_id": f"W{i}",
            "domain": "biology" if i % 2 else "materials_science",
            "abstract": f"A membrane transports sodium ions, potassium ions and chloride ions under a concentration gradient. Experiment {i}.",
        }
        for i in range(count)
    ]
    (raw / "papers.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    return settings


def test_batch_and_task_cache_replay(tmp_path):
    settings = make_settings(tmp_path)
    client = FakeClient(settings)
    first = asyncio.run(run(settings, gateway=CachedGateway(client)))
    assert first["mechanism_count"] == 8
    assert client.calls == 1
    second = asyncio.run(run(settings, gateway=CachedGateway(client)))
    assert second["usage"]["task_cache_hits"] == 8
    assert second["usage"]["gateway_calls"] == 0
    assert client.calls == 1
    assert first["files"]["mechanisms.jsonl"] == second["files"]["mechanisms.jsonl"]
    assert second["human_accuracy"] is None
    assert (tmp_path / "normalized/concepts.parquet").exists()


def test_repair_and_failure_recording(tmp_path):
    settings = make_settings(tmp_path)
    client = FakeClient(settings, invalid_first=True)
    failed = asyncio.run(run(settings, gateway=CachedGateway(client)))
    assert failed["failed_papers"] == 8
    repaired = asyncio.run(
        run(settings, gateway=CachedGateway(client), retries=2, retry_failed=True)
    )
    assert repaired["mechanism_count"] == 8
    assert client.calls == 2


def test_automatic_repair(tmp_path):
    settings = make_settings(tmp_path)
    client = FakeClient(settings, invalid_first=True)
    report = asyncio.run(run(settings, gateway=CachedGateway(client), retries=2))
    assert report["failed_papers"] == 0
    assert report["usage"]["paper_attempts"] == 16


def test_missing_key_preserves_previous_outputs(tmp_path):
    settings = make_settings(tmp_path)
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    previous = normalized / "mechanisms.jsonl"
    previous.write_text("previous snapshot", encoding="utf-8")
    from conceptbridge.common.llm import LLMUnavailable

    with pytest.raises(LLMUnavailable):
        asyncio.run(run(settings))
    assert previous.read_text(encoding="utf-8") == "previous snapshot"


def test_oversized_limit_and_duplicate_input(tmp_path):
    settings = make_settings(tmp_path, count=1)
    with pytest.raises(ValueError, match="only 1"):
        asyncio.run(run(settings))
    source = tmp_path / "raw/papers.jsonl"
    source.write_text(source.read_text() + "\n" + source.read_text(), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        asyncio.run(run(settings, limit=1))


def test_p2_graph_round_trip_and_install(tmp_path, monkeypatch):
    from conceptbridge.graph.store import GraphStore
    from conceptbridge.match.pipeline import build_result, load_corpus

    settings = make_settings(tmp_path)
    asyncio.run(run(settings, gateway=CachedGateway(FakeClient(settings))))
    output = tmp_path / "fixtures"
    report = export_bundle(settings, output, paper_count=2, mechanism_count=2, install_index=True)
    store = GraphStore.load(output / "graph.min")
    assert len(store.all_mechanisms()) == 2
    assert (output / "graph.min.pkl").read_bytes() == (output / "graph.min/graph.pkl").read_bytes()
    monkeypatch.setattr("conceptbridge.match.pipeline.get_settings", lambda: settings)
    units, version = load_corpus()
    assert len(units) == 2
    assert "installed_index" in report
    result = build_result("membrane", units, "materials_science", 5, [], graph_version=version)
    assert len(result.bridges) == 1
    assert result.bridges[0].target_domain == "biology"


def test_small_corpus_cannot_fake_fixture_counts(tmp_path):
    settings = make_settings(tmp_path)
    asyncio.run(run(settings, gateway=CachedGateway(FakeClient(settings))))
    output = tmp_path / "fixtures"
    with pytest.raises(ValueError, match="insufficient"):
        export_bundle(settings, output)
    assert not output.exists()


def test_gateway_coalesces_identical_requests(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path, llm_api_key="test-only", _env_file=None)
    client = LLMClient(settings)
    calls = []

    async def post(payload):
        calls.append(payload)
        return {"papers": []}

    monkeypatch.setattr(client, "_post", post)
    gateway = CachedGateway(client)

    async def twice():
        return await asyncio.gather(
            gateway.complete("system", "user"), gateway.complete("system", "user")
        )

    assert asyncio.run(twice()) == [{"papers": []}, {"papers": []}]
    assert len(calls) == 1
    assert gateway.stats == {"requests": 2, "cache_hits": 1, "gateway_calls": 1}
    usage = json.loads(client.usage_path.read_text())
    assert usage["calls"] == 1


def test_full_fixture_counts_and_size(tmp_path):
    from conceptbridge.graph.store import GraphStore

    settings = make_settings(tmp_path, count=200)
    client = FakeClient(settings, mechanism_count=3)
    report = asyncio.run(run(settings, limit=200, gateway=CachedGateway(client)))
    assert report["mechanism_count"] == 600
    output = tmp_path / "fixtures"
    bundle = export_bundle(settings, output)
    assert bundle["paper_count"] == 200
    assert bundle["mechanism_count"] == 500
    assert len(GraphStore.load(output / "graph.min").all_mechanisms()) == 500
    assert sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) < 5_000_000


def test_cli_defaults_preview_and_missing_configuration(tmp_path, monkeypatch):
    from conceptbridge.extract.cli import main

    settings = make_settings(tmp_path)
    monkeypatch.setattr("conceptbridge.extract.cli.get_settings", lambda: settings)
    assert main(["--dry-run"]) == 0
    assert main([]) == 1
    with pytest.raises(SystemExit) as error:
        main(["--limit", "0"])
    assert error.value.code == 2


def test_explicit_retry_avoids_cached_invalid_response(tmp_path, monkeypatch):
    settings = make_settings(tmp_path)
    settings.llm_api_key = "test-only"
    client = LLMClient(settings)
    responder = FakeClient(settings, invalid_first=True)

    async def post(payload):
        return await responder.complete_json(user=payload["messages"][1]["content"])

    monkeypatch.setattr(client, "_post", post)
    first = asyncio.run(run(settings, gateway=CachedGateway(client)))
    assert first["failed_papers"] == 8
    second = asyncio.run(run(settings, gateway=CachedGateway(client), retry_failed=True))
    assert second["failed_papers"] == 0
    assert responder.calls == 2


def test_changed_source_preserves_completed_tasks(tmp_path):
    settings = make_settings(tmp_path)
    client = FakeClient(settings)
    original = client.complete_json

    async def change_source(**kwargs):
        response = await original(**kwargs)
        with (tmp_path / "raw/papers.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("\n")
        return response

    client.complete_json = change_source
    with pytest.raises(ValueError, match="source changed"):
        asyncio.run(run(settings, gateway=CachedGateway(client)))
    assert len(list((tmp_path / "normalized/task_cache").glob("*.json"))) == 8
    assert not (tmp_path / "normalized/current.json").exists()


def test_export_cli_for_pilot_bundle(tmp_path, monkeypatch):
    from conceptbridge.extract.export import main

    settings = make_settings(tmp_path)
    asyncio.run(run(settings, gateway=CachedGateway(FakeClient(settings))))
    monkeypatch.setattr("conceptbridge.extract.export.get_settings", lambda: settings)
    output = tmp_path / "pilot-fixtures"
    assert main(["--output", str(output), "--paper-count", "8", "--mechanism-count", "8"]) == 0
    assert (output / "p1.manifest.json").exists()
