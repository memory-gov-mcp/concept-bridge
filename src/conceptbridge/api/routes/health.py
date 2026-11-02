"""存活探针 + 图规模。前端启屏先打这个。"""

from __future__ import annotations

from fastapi import APIRouter

from ...common.config import fixture_path, get_settings
from ...common.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="存活与图状态")
def health() -> HealthResponse:
    settings = get_settings()
    graph_ready = (settings.resolved_data_dir / "index").exists() or fixture_path(
        "graph.min.pkl"
    ).exists()
    return HealthResponse(
        status="ok" if graph_ready else "degraded",
        version="0.1.0",
        graph_version="g-20261102-0",
        graph_ready=graph_ready,
        demo_mode=settings.demo_mode,
    )
