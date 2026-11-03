"""编排层韧性测试：超时、异常、降级、离线。

这几条是"技术实现 40%"里最实在的部分——评委现场最容易遇到的问题不是算法不准，
是网络抖一下、算法抛个异常、页面转圈十分钟。这里的每个用例都在证明"不会那样"。
"""

from __future__ import annotations

import asyncio
import json

import pytest

from conceptbridge.api.services import bridge_service
from conceptbridge.common.config import fixture_path, get_settings
from conceptbridge.common.schemas import BridgeRequest, BridgeResult


@pytest.fixture(autouse=True)
def _reset_settings():
    """settings 是 lru_cache 的，每个用例前后都要清，否则 env 不生效。"""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _req(**kw: object) -> BridgeRequest:
    return BridgeRequest(query="锂枝晶抑制", **kw)  # type: ignore[arg-type]


def _fixture_result(*, stub: bool = False) -> BridgeResult:
    raw = json.loads(fixture_path("bridge.sample.json").read_text(encoding="utf-8"))
    raw["meta"] = {**raw["meta"], "stub": stub, "latency_ms": 999}
    return BridgeResult.model_validate(raw)


def test_timeout_degrades_instead_of_hanging(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_runner(*_: object, **__: object) -> BridgeResult:
        await asyncio.sleep(5)
        raise AssertionError("不应该跑到这里")

    monkeypatch.setattr(bridge_service, "_load_real_runner", lambda: slow_runner)
    monkeypatch.setenv("DEMO_MODE", "0")
    monkeypatch.setenv("BRIDGE_TIMEOUT_S", "0.05")
    get_settings.cache_clear()

    result = asyncio.run(bridge_service.run_bridge(_req()))

    assert result.meta.degraded is True
    assert result.meta.stub is True
    assert result.bridges, "降级也必须给结果，不能给空页"


def test_runner_exception_degrades(monkeypatch: pytest.MonkeyPatch) -> None:
    async def broken_runner(*_: object, **__: object) -> BridgeResult:
        raise RuntimeError("P2 的实现炸了")

    monkeypatch.setattr(bridge_service, "_load_real_runner", lambda: broken_runner)
    monkeypatch.setenv("DEMO_MODE", "0")
    get_settings.cache_clear()

    result = asyncio.run(bridge_service.run_bridge(_req()))

    assert result.meta.degraded is True
    assert result.bridges


def test_runner_success_is_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    base = _fixture_result(stub=False)

    async def ok_runner(*_: object, **__: object) -> BridgeResult:
        return base

    monkeypatch.setattr(bridge_service, "_load_real_runner", lambda: ok_runner)
    monkeypatch.setenv("DEMO_MODE", "0")
    get_settings.cache_clear()

    result = asyncio.run(bridge_service.run_bridge(_req()))

    assert result.meta.degraded is False
    assert result.meta.latency_ms != 999, "必须用实测延迟覆盖实现层报的延迟"


def test_no_runner_degrades_but_still_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bridge_service, "_load_real_runner", lambda: None)
    monkeypatch.setenv("DEMO_MODE", "0")
    get_settings.cache_clear()

    result = asyncio.run(bridge_service.run_bridge(_req()))

    assert result.meta.degraded is True
    assert result.meta.stub is True


def test_demo_mode_never_loads_the_real_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """离线演示的硬保证：连"尝试找实现"这一步都不做。"""

    def boom() -> None:
        raise AssertionError("DEMO_MODE 下不允许触碰真实实现")

    monkeypatch.setattr(bridge_service, "_load_real_runner", boom)
    monkeypatch.setenv("DEMO_MODE", "1")
    get_settings.cache_clear()

    result = asyncio.run(bridge_service.run_bridge(_req()))

    assert result.meta.stub is True
    assert result.meta.degraded is False, "演示模式下不算降级，这是正常路径"


def test_exclude_and_top_k_are_respected() -> None:
    get_settings.cache_clear()
    one = asyncio.run(bridge_service.run_bridge(_req(top_k=1)))
    assert len(one.bridges) == 1

    none_left = asyncio.run(bridge_service.run_bridge(_req(exclude_domains=["biology"])))
    assert none_left.bridges == []
    assert none_left.meta.candidates >= 0
