"""SSE 流式接口：阶段帧 + 结果帧必须都合法。"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from conceptbridge.api.main import app
from conceptbridge.common.schemas import BridgeResult


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _frames(body: str) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for block in body.strip().split("\n\n"):
        event = None
        data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[len("event: ") :]
            elif line.startswith("data: "):
                data = line[len("data: ") :]
        if event and data:
            out.append((event, json.loads(data)))
    return out


def test_stream_emits_stages_then_result(client: TestClient) -> None:
    r = client.post("/api/v1/bridge/stream", json={"query": "锂枝晶抑制", "top_k": 2})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    frames = _frames(r.text)
    events = [e for e, _ in frames]

    assert events.count("stage") == 3
    assert events[-2:] == ["result", "done"], "结果必须最后一帧之前推完"

    result_payload = next(p for e, p in frames if e == "result")
    result = BridgeResult.model_validate(result_payload)
    assert result.query == "锂枝晶抑制"
    assert len(result.bridges) <= 2

    done = next(p for e, p in frames if e == "done")
    assert done["ok"] is True
