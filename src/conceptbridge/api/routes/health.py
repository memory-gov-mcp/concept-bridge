"""存活探针 + 图状态。

RFC-P1-002：`graph_version` 必须来自当前快照，不能写死，
否则前端显示的版本和实际图谱对不上。
"""

from __future__ import annotations

from fastapi import APIRouter

from ...common.config import get_settings
from ...common.schemas import HealthResponse
from ..services.snapshot import current_snapshot

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="存活与图状态")
def health() -> HealthResponse:
    settings = get_settings()
    snapshot = current_snapshot()

    # graph_ready 表示"装了真实索引快照"，而不是"有 fixture 能应付"
    graph_ready = snapshot.source == "index"
    # 演示模式本来就用预置样例，不算降级
    ok = graph_ready or settings.demo_mode

    return HealthResponse(
        status="ok" if ok else "degraded",
        version="0.1.0",
        graph_version=snapshot.version,
        graph_ready=graph_ready,
        demo_mode=settings.demo_mode,
    )
