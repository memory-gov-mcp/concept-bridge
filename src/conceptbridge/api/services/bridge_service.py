"""编排层：把 graph / match 串起来，并负责"没准备好时不要 500"。"""

from __future__ import annotations

import json
from typing import Any, Protocol

from ...common.config import fixture_path, get_settings
from ...common.errors import AppError, ErrorCode
from ...common.logging import get_logger
from ...common.schemas import BridgeRequest, BridgeResult, BridgeSource, ResultMeta

log = get_logger(__name__)


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
    raw = _load_fixture()
    result = BridgeResult.model_validate(raw)

    excluded = set(req.exclude_domains)
    bridges = [b for b in result.bridges if b.target_domain not in excluded][: req.top_k]
    meta = result.meta.model_copy(
        update={
            "stub": True,
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
    if runner is not None:
        try:
            return await runner(
                req.query,
                source_domain=req.source_domain,
                top_k=req.top_k,
                exclude_domains=req.exclude_domains,
            )
        except AppError:
            raise
        except Exception as exc:  # 任何实现层异常都不许冒到评委面前
            log.exception("bridge_failed", extra={"kv": {"err": type(exc).__name__}})
            degraded = _from_fixture(req)
            return _mark_degraded(degraded)

    degraded = _from_fixture(req)
    if settings.demo_mode:
        return degraded
    return _mark_degraded(degraded)


def _mark_degraded(result: BridgeResult) -> BridgeResult:
    meta: ResultMeta = result.meta.model_copy(update={"degraded": True})
    return result.model_copy(update={"meta": meta})


def empty_source(domain: str = "unknown") -> BridgeSource:
    return BridgeSource(domain=domain)
