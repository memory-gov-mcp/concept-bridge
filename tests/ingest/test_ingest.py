import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from conceptbridge.common.config import Settings
from conceptbridge.ingest.cli import collect, main
from conceptbridge.ingest.normalize_text import normalize_work, restore_abstract
from conceptbridge.ingest.openalex import fetch_page
from conceptbridge.match.config import domain_distance


@pytest.fixture
def works():
    return json.loads(Path(__file__).with_name("openalex_works.json").read_text(encoding="utf-8"))


def test_recorded_responses_and_p2_domains(works):
    papers = [normalize_work(work) for work in works]
    assert [paper["domain"] for paper in papers] == [
        "materials_science",
        "biology",
        "computer_science",
    ]
    for work, paper in zip(works, papers, strict=True):
        assert paper["paper_id"] == work["id"].rsplit("/", 1)[-1]
        tokens = paper["abstract"].split(" ")
        for word, positions in work["abstract_inverted_index"].items():
            assert all(tokens[position] == word for position in positions)
    assert domain_distance(papers[0]["domain"], papers[1]["domain"]) == 1.0


@pytest.mark.parametrize("index", [{"a": [1]}, {"a": [0], "b": [0]}, {"a": [-1]}, {"a": [True]}])
def test_reject_corrupt_positions(index):
    with pytest.raises(ValueError):
        restore_abstract(index)


def test_empty_abstract_and_unknown_field(works):
    assert restore_abstract(None) == ""
    work = {**works[0], "primary_topic": None}
    with pytest.raises(ValueError, match="field"):
        normalize_work(work)


def test_resume_dedup_and_larger_limit(tmp_path, works):
    calls = []

    def respond(request):
        calls.append(dict(request.url.params))
        page = request.url.params["page"]
        results = [works[0]] if page == "1" else [works[0], works[1], works[2]]
        return httpx.Response(200, json={"results": results, "meta": {"count": 400}})

    settings = Settings(data_dir=tmp_path, _env_file=None)
    queries = (("materials_science", "25", "lithium dendrite"),)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        collect(settings, limit=1, client=client, queries=queries)
        # This simulates publication being interrupted after committing the checkpoint.
        (tmp_path / "raw/papers.jsonl").write_text("incomplete", encoding="utf-8")
        collect(settings, limit=1, client=client, queries=queries)
        assert len(calls) == 1
        result = collect(settings, limit=3, client=client, queries=queries)
    assert result["paper_count"] == 3
    assert [call["page"] for call in calls] == ["1", "2"]
    papers = [
        json.loads(line)
        for line in (tmp_path / "raw/papers.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len({paper["paper_id"] for paper in papers}) == 3


def test_retry_http_errors(monkeypatch):
    monkeypatch.setattr("conceptbridge.ingest.openalex.time.sleep", lambda _: None)
    statuses = iter([429, 503, 200])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(next(statuses), json={"results": [], "meta": {"count": 0}})
        )
    ) as client:
        assert fetch_page(client, {})["results"] == []


def test_demo_never_calls_network(tmp_path):
    def unexpected(_):
        pytest.fail("DEMO_MODE attempted network")

    settings = Settings(data_dir=tmp_path, demo_mode=True, _env_file=None)
    with (
        httpx.Client(transport=httpx.MockTransport(unexpected)) as client,
        pytest.raises(ValueError, match="DEMO_MODE"),
    ):
        collect(settings, limit=1, client=client)


def test_invalid_limit():
    with pytest.raises(SystemExit) as error:
        main(["--limit", "0"])
    assert error.value.code == 2


@pytest.mark.parametrize("body", [{}, {"results": [], "meta": []}])
def test_malformed_response_is_rejected(body):
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))
        ) as client,
        pytest.raises(ValueError),
    ):
        fetch_page(client, {})


def test_bad_paper_is_recorded_and_exhaustion_is_incomplete(tmp_path, works):
    work = {**works[0], "abstract_inverted_index": {"broken": [1]}}
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"results": [work], "meta": {"count": 1}})
        )
    ) as client:
        result = collect(Settings(data_dir=tmp_path, _env_file=None), limit=1, client=client)
    assert result["paper_count"] == 0
    assert result["failure_count"] == 1
    assert result["complete"] is False


def test_unused_page_records_resume_offline(tmp_path, works):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"results": works, "meta": {"count": 3}})

    settings = Settings(data_dir=tmp_path, _env_file=None)
    queries = (("materials_science", "25", "lithium dendrite"),)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert collect(settings, limit=1, client=client, queries=queries)["paper_count"] == 1
        settings.demo_mode = True
        assert collect(settings, limit=3, client=client, queries=queries)["paper_count"] == 3
    assert len(calls) == 1


def test_failed_page_keeps_checkpoint_and_records_error(tmp_path, works):
    def respond(request):
        if request.url.params["page"] == "1":
            return httpx.Response(200, json={"results": [works[0]], "meta": {"count": 400}})
        return httpx.Response(401)

    settings = Settings(data_dir=tmp_path, _env_file=None)
    queries = (("materials_science", "25", "lithium dendrite"),)
    with (
        httpx.Client(transport=httpx.MockTransport(respond)) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        collect(settings, limit=3, client=client, queries=queries)
    checkpoint = json.loads((tmp_path / "raw/checkpoint.json").read_text(encoding="utf-8"))
    assert len(checkpoint["papers"]) == 1
    assert checkpoint["pages"]["lithium dendrite"] == 2
    assert checkpoint["failures"]["request:lithium dendrite"]["status_code"] == 401


def test_concurrent_writer_is_rejected(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    lock = sqlite3.connect(raw / ".ingest-lock.sqlite3")
    try:
        lock.execute("BEGIN IMMEDIATE")
        with httpx.Client() as client, pytest.raises(sqlite3.OperationalError, match="locked"):
            collect(Settings(data_dir=tmp_path, _env_file=None), limit=1, client=client)
    finally:
        lock.close()


@pytest.mark.parametrize("status,expected", [(200, 0), (401, 1)])
def test_cli_entrypoint(tmp_path, monkeypatch, works, status, expected):
    settings = Settings(data_dir=tmp_path, _env_file=None)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(status, json={"results": works, "meta": {"count": 3}})
        )
    )
    monkeypatch.setattr("conceptbridge.ingest.cli.get_settings", lambda: settings)
    monkeypatch.setattr("conceptbridge.ingest.cli.httpx.Client", lambda **kwargs: client)
    assert main(["--limit", "1"]) == expected
