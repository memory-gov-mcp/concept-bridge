"""API 层行为测试。这里只测"契约与降级"，不测算法。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conceptbridge.api.main import app
from conceptbridge.common.schemas import BridgeResult


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["version"]


def test_bridge_returns_valid_payload(client: TestClient) -> None:
    r = client.post("/api/v1/bridge", json={"query": "锂枝晶抑制", "top_k": 3})
    assert r.status_code == 200
    result = BridgeResult.model_validate(r.json())
    assert result.bridges, "至少返回一条桥"
    for b in result.bridges:
        assert b.target_domain != result.source.domain
        assert b.citations
    assert result.meta.candidates >= len(result.bridges)


def test_bridge_rejects_short_query(client: TestClient) -> None:
    r = client.post("/api/v1/bridge", json={"query": "a"})
    assert r.status_code == 422


def test_bridge_top_k_is_respected(client: TestClient) -> None:
    r = client.post("/api/v1/bridge", json={"query": "锂枝晶抑制", "top_k": 1})
    assert r.status_code == 200
    assert len(r.json()["bridges"]) <= 1


def test_mechanism_detail_and_404(client: TestClient) -> None:
    r = client.get("/api/v1/mechanisms/mu_01J9A2K7")
    assert r.status_code == 200
    assert r.json()["id"] == "mu_01J9A2K7"
    assert client.get("/api/v1/mechanisms/nope").status_code == 404


def test_subgraph_and_404(client: TestClient) -> None:
    r = client.get("/api/v1/graph/subgraph", params={"concept_id": "c_sei_film", "hops": 2})
    assert r.status_code == 200
    assert r.json()["subgraph"]["nodes"]
    assert client.get("/api/v1/graph/subgraph", params={"concept_id": "nope"}).status_code == 404


def test_eval_report_shape(client: TestClient) -> None:
    r = client.get("/api/v1/eval/report")
    assert r.status_code == 200
    assert "rows" in r.json()
