"""RFC-P1-002 验收：四个端点必须读同一份图谱快照。

覆盖三条验收条件：
1. `/bridge` 返回的机制 ID，在 `/mechanisms/{id}` 可访问（不再 404）；
2. `/bridge` 涉及的每个概念，在 `/graph/subgraph` 都有邻域；
3. `/health` 的 `graph_version` 与 `/bridge` 的 `meta.graph_version` 一致。

这些用例走 fixture 兜底路径，因此不需要 numpy / networkx，可在最小安装下运行。
真实索引快照的路径由 CI（`uv sync --extra analyze`）覆盖。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conceptbridge.api.main import app
from conceptbridge.api.services.snapshot import current_snapshot, reset_snapshot_cache
from conceptbridge.common.config import get_settings


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_snapshot():
    get_settings.cache_clear()
    reset_snapshot_cache()
    yield
    get_settings.cache_clear()
    reset_snapshot_cache()


def _bridge(client: TestClient) -> dict:
    r = client.post("/api/v1/bridge", json={"query": "锂枝晶抑制", "top_k": 3})
    assert r.status_code == 200, r.text
    return r.json()


def _all_mechanism_ids(body: dict) -> list[str]:
    ids = [m["id"] for m in body["source"]["mechanisms"]]
    ids += [b["target_mechanism"]["id"] for b in body["bridges"]]
    return ids


def _all_concept_ids(body: dict) -> set[str]:
    ids = {n["id"] for n in body["source"]["subgraph"]["nodes"]}
    for bridge in body["bridges"]:
        for pair in bridge.get("alignment") or []:
            ids.add(pair["source_concept_id"])
            ids.add(pair["target_concept_id"])
    return ids


def test_bridge_mechanism_ids_are_resolvable(client: TestClient) -> None:
    body = _bridge(client)
    ids = _all_mechanism_ids(body)
    assert ids, "bridge 必须返回机制，否则这条验收没有意义"

    for mechanism_id in ids:
        r = client.get(f"/api/v1/mechanisms/{mechanism_id}")
        assert r.status_code == 200, f"{mechanism_id} 详情 404（快照不一致）"
        assert r.json()["id"] == mechanism_id


def test_bridge_concepts_have_neighbourhood(client: TestClient) -> None:
    body = _bridge(client)
    concept_ids = _all_concept_ids(body)
    assert concept_ids

    for concept_id in concept_ids:
        r = client.get("/api/v1/graph/subgraph", params={"concept_id": concept_id, "hops": 2})
        assert r.status_code == 200, f"{concept_id} 邻域 404（快照不一致）"
        assert r.json()["subgraph"]["nodes"], f"{concept_id} 邻域为空"


def test_all_endpoints_report_same_version(client: TestClient) -> None:
    body = _bridge(client)
    health = client.get("/api/v1/health").json()

    assert health["graph_version"] == body["meta"]["graph_version"]
    if current_snapshot().source == "fixture":
        assert health["graph_ready"] is False, "fixture 兜底不能声称 graph_ready"


def test_unknown_ids_return_404(client: TestClient) -> None:
    assert client.get("/api/v1/mechanisms/not-a-real-id").status_code == 404
    assert (
        client.get("/api/v1/graph/subgraph", params={"concept_id": "not-a-real-id"}).status_code
        == 404
    )


def test_falls_back_to_fixture_without_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """没有 data/index 时必须退化到 fixture，而不是 503。

    用"不存在的相对路径"而不是 tmp_path：这个用例不需要写盘，
    也让它在只读沙箱里也能跑。
    """
    monkeypatch.setenv("DATA_DIR", ".no-such-index-dir")
    get_settings.cache_clear()
    reset_snapshot_cache()

    snapshot = current_snapshot()
    assert snapshot.source == "fixture"
    assert snapshot.mechanisms
    assert snapshot.nodes, "fixture 也要能回答邻域查询"
