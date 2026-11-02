"""主接口：一次查询 → 一组跨域桥。"""

from __future__ import annotations

from fastapi import APIRouter

from ...common.schemas import BridgeRequest, BridgeResult
from ..services.bridge_service import run_bridge

router = APIRouter(tags=["bridge"])


@router.post(
    "/bridge",
    response_model=BridgeResult,
    summary="跨域结构类比检索",
    response_description="源机制、跨域桥、假设与引用",
)
async def create_bridge(req: BridgeRequest) -> BridgeResult:
    return await run_bridge(req)
