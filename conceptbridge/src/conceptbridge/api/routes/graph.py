"""子图查询：前端画双域图时按需拉取邻域。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from ...common.config import fixture_path
from ...common.errors import AppError, ErrorCode
from ...common.schemas import Subgraph, SubgraphResponse

router = APIRouter(tags=["graph"])


@router.get("/graph/subgraph", response_model=SubgraphResponse, summary="概念 N 跳子图")
def get_subgraph(
    concept_id: str = Query(..., min_length=1),
    hops: int = Query(default=2, ge=1, le=3),
) -> SubgraphResponse:
    path = fixture_path("bridge.sample.json")
    if not path.exists():
        raise AppError(ErrorCode.GRAPH_NOT_READY, "还没有图数据", 503)
    raw = json.loads(path.read_text(encoding="utf-8"))
    subgraph = Subgraph.model_validate(raw["source"]["subgraph"])

    # P2 接管后替换为真实邻域扩展；当前只回源子图，保证前端有东西可画
    node_ids = {n.id for n in subgraph.nodes}
    if concept_id not in node_ids:
        raise AppError(ErrorCode.NOT_FOUND, f"概念 {concept_id} 不在图中", 404)

    return SubgraphResponse(concept_id=concept_id, hops=hops, subgraph=subgraph)
