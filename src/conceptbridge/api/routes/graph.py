"""子图查询：前端画双域图时按需拉取邻域。

RFC-P1-002：走与 `/bridge` 相同的快照。有索引快照时用 GraphStore 做真实邻域扩展，
fixture 兜底时退化为本地 BFS，跳数语义保持一致。
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from ...common.schemas import SubgraphResponse
from ..services.snapshot import subgraph_for

router = APIRouter(tags=["graph"])


@router.get("/graph/subgraph", response_model=SubgraphResponse, summary="概念 N 跳子图")
def get_subgraph(
    concept_id: str = Query(..., min_length=1),
    hops: int = Query(default=2, ge=1, le=3),
) -> SubgraphResponse:
    return SubgraphResponse(
        concept_id=concept_id,
        hops=hops,
        subgraph=subgraph_for(concept_id, hops=hops),
    )
