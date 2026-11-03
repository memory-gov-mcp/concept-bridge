"""主接口：一次查询 → 一组跨域桥。同步与流式两条。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...common.schemas import BridgeRequest, BridgeResult
from ..services.bridge_service import run_bridge, run_bridge_stream

router = APIRouter(tags=["bridge"])


@router.post(
    "/bridge",
    response_model=BridgeResult,
    summary="跨域结构类比检索",
    response_description="源机制、跨域桥、假设与引用",
)
async def create_bridge(req: BridgeRequest) -> BridgeResult:
    return await run_bridge(req)


@router.post(
    "/bridge/stream",
    summary="跨域检索（SSE 渐进返回）",
    response_description="event: stage / result / done",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_bridge(req: BridgeRequest) -> StreamingResponse:
    return StreamingResponse(
        run_bridge_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
