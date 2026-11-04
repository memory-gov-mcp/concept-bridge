"""机制详情：前端点击图谱节点时用。

RFC-P1-002：必须与 `/bridge` 读同一份快照，否则真实语料返回的 ID 在这里会 404。
"""

from __future__ import annotations

from fastapi import APIRouter

from ...common.schemas import MechanismUnit
from ..services.snapshot import find_mechanism

router = APIRouter(tags=["mechanism"])


@router.get("/mechanisms/{mechanism_id}", response_model=MechanismUnit, summary="机制详情")
def get_mechanism(mechanism_id: str) -> MechanismUnit:
    return find_mechanism(mechanism_id)
