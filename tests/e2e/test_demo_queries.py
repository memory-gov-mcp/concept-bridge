"""e2e 冒烟：答辩时要演示的 3 条 query 必须始终能出结果。

`uv run task check` 不跑这个（会慢），`uv run task e2e` 才跑。
Day1 集成窗口必须绿。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conceptbridge.api.main import app
from conceptbridge.common.schemas import BridgeResult

DEMO_QUERIES = ["锂枝晶抑制", "催化剂失活", "蛋白质折叠"]


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("query", DEMO_QUERIES)
def test_demo_query_end_to_end(client: TestClient, query: str) -> None:
    r = client.post("/api/v1/bridge", json={"query": query, "top_k": 3})
    assert r.status_code == 200, r.text
    result = BridgeResult.model_validate(r.json())
    assert result.query == query
    assert result.bridges, f"{query} 没返回任何桥"
