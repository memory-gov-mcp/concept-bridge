"""编排层：把 graph / match 串起来，并负责"没准备好时不要 500"。

三条纪律：
1. 硬超时。任何实现层慢过 `BRIDGE_TIMEOUT_S` 都必须降级返回，不许把评委挂在转圈上。
2. 降级有标记。`degraded=True` 与 `stub=True` 是两件事：前者是算不动了，后者是还没接算法。
3. 实现层抛什么都吞掉。宁可返回少一条桥，也不能返回 traceback。
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any, Protocol

from ...common.config import fixture_path, get_settings
from ...common.errors import AppError, ErrorCode
from ...common.logging import get_logger
from ...common.schemas import BridgeRequest, BridgeResult
from .snapshot import current_snapshot

log = get_logger(__name__)

# 流式接口的分阶段节奏。纯粹为了前端能做"召回 → 打分 → 生成"的渐进呈现。
_STAGE_DELAY_S = 0.08


class BridgeRunner(Protocol):
    """P2 的 match 层需要实现的接口。签名冻结，改动需 RFC。"""

    async def __call__(
        self,
        query: str,
        source_domain: str | None = None,
        top_k: int = 5,
        exclude_domains: list[str] | None = None,
    ) -> BridgeResult: ...


def _load_real_runner() -> BridgeRunner | None:
    """P2 落地 match/pipeline.py 后自动接管，无需改 API。"""
    try:
        from ...match.pipeline import run_bridge  # type: ignore[import-not-found]

        return run_bridge  # type: ignore[no-any-return]
    except Exception:
        return None


def _load_fixture() -> dict[str, Any]:
    path = fixture_path("bridge.sample.json")
    if not path.exists():
        raise AppError(ErrorCode.GRAPH_NOT_READY, "图谱未构建且没有 fixture 兜底", 503)
    return json.loads(path.read_text(encoding="utf-8"))


def _from_fixture(req: BridgeRequest) -> BridgeResult:
    """兜底路径。返回的东西必须完全合法——演示时评委看到的不能是半成品。

    `graph_version` 统一取当前快照的版本，不用 fixture JSON 里写死的那个：
    否则 `/bridge` 报 `g-2026...`、`/health` 报 `fixtures`，同一个页面两个版本号（RFC-P1-002）。
    """
    raw = _load_fixture()
    result = BridgeResult.model_validate(raw)

    excluded = set(req.exclude_domains)
    bridges = [b for b in result.bridges if b.target_domain not in excluded][: req.top_k]
    meta = result.meta.model_copy(
        update={
            "stub": True,
            "graph_version": current_snapshot().version,
            "latency_ms": max(0, result.meta.latency_ms // 10),
            "candidates": max(result.meta.candidates, len(bridges)),
        }
    )
    updated = result.model_copy(update={"query": req.query, "bridges": bridges, "meta": meta})
    # 重新走一遍校验，保证降级路径也满足全部不变式
    return BridgeResult.model_validate(updated.model_dump())


async def run_bridge(req: BridgeRequest) -> BridgeResult:
    settings = get_settings()

    runner = None if settings.demo_mode else _load_real_runner()
    if runner is None:
        fixture = _from_fixture(req)
        return fixture if settings.demo_mode else _mark_degraded(fixture)

    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            runner(
                req.query,
                source_domain=req.source_domain,
                top_k=req.top_k,
                exclude_domains=req.exclude_domains,
            ),
            timeout=settings.bridge_timeout_s,
        )
    except TimeoutError:
        log.warning(
            "bridge_timeout",
            extra={"kv": {"timeout_s": settings.bridge_timeout_s, "query_len": len(req.query)}},
        )
        return _mark_degraded(_from_fixture(req))
    except AppError:
        raise
    except Exception as exc:  # 实现层任何异常都不许冒到评委面前
        log.exception("bridge_failed", extra={"kv": {"err": type(exc).__name__}})
        return _mark_degraded(_from_fixture(req))

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    meta = result.meta.model_copy(update={"latency_ms": elapsed_ms, "degraded": False})
    return result.model_copy(update={"meta": meta})


def sse_event(name: str, payload: dict[str, Any]) -> str:
    """SSE 帧。手动拼而不用 sse-starlette——少一个依赖，少一种现场故障。"""
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def run_bridge_stream(req: BridgeRequest) -> AsyncIterator[str]:
    """给前端做渐进呈现用。先报阶段，最后把完整结果一次性推下去。

    阶段只是节奏提示，不承诺真实进度——**不要**让前端把 progress 当百分比显示，
    否则真实算法接进来后进度会跳。
    """
    stages = (
        ("recall", "召回候选机制", 0.2),
        ("score", "结构签名打分", 0.55),
        ("generate", "生成假设与引用", 0.85),
    )
    for name, label, progress in stages:
        yield sse_event("stage", {"stage": name, "label": label, "progress": progress})
        await asyncio.sleep(_STAGE_DELAY_S)

    result = await run_bridge(req)
    yield sse_event("result", result.model_dump(mode="json"))
    yield sse_event(
        "done",
        {
            "ok": True,
            "degraded": result.meta.degraded,
            "stub": result.meta.stub,
            "latency_ms": result.meta.latency_ms,
        },
    )


def _mark_degraded(result: BridgeResult) -> BridgeResult:
    meta = result.meta.model_copy(update={"degraded": True})
    return result.model_copy(update={"meta": meta})
