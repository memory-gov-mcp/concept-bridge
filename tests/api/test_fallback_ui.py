"""离线极简界面：不依赖 node_modules / 构建产物也能在浏览器里看到桥。

这条兜底针对的是"前端依赖装不上"——断网、CI 缓存失效、或评委机器没有 Node。
页面直接打现成的 `/api/v1/*`，所以只要 API 能起就能看。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conceptbridge.api.main import FALLBACK_UI, app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_root_serves_offline_ui(client: TestClient) -> None:
    assert FALLBACK_UI.exists(), "兜底页面文件缺失，离线时就没有界面可看了"

    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert "/api/v1/bridge" in body, "页面必须直连真实接口，不能只放静态文案"
    assert "/api/v1/health" in body
    # 兜底页必须自包含：不引用任何构建产物或打包器资源
    assert "/node_modules/" not in body
    assert "<script src=" not in body, "不允许外部脚本，断网时会白屏"


def test_offline_ui_is_not_part_of_contract(client: TestClient) -> None:
    """兜底页不进 OpenAPI，否则契约漂移测试会误报，前端也会把它当成正式接口。"""
    spec = client.get("/openapi.json").json()
    assert "/" not in spec["paths"]


def test_api_routes_still_work(client: TestClient) -> None:
    assert client.get("/api/v1/health").status_code == 200
    assert client.post("/api/v1/bridge", json={"query": "锂枝晶抑制", "top_k": 1}).status_code == 200
