"""机制详情：前端点击图谱节点时用。"""

from __future__ import annotations

import json

from fastapi import APIRouter

from ...common.config import fixture_path
from ...common.errors import AppError, ErrorCode
from ...common.schemas import MechanismUnit

router = APIRouter(tags=["mechanism"])


def _all_mechanisms() -> list[MechanismUnit]:
    path = fixture_path("bridge.sample.json")
    if not path.exists():
        raise AppError(ErrorCode.GRAPH_NOT_READY, "还没有机制数据", 503)
    raw = json.loads(path.read_text(encoding="utf-8"))
    found: list[MechanismUnit] = []
    for m in raw.get("source", {}).get("mechanisms", []):
        found.append(MechanismUnit.model_validate(m))
    for b in raw.get("bridges", []):
        found.append(MechanismUnit.model_validate(b["target_mechanism"]))
    return found


@router.get("/mechanisms/{mechanism_id}", response_model=MechanismUnit, summary="机制详情")
def get_mechanism(mechanism_id: str) -> MechanismUnit:
    for m in _all_mechanisms():
        if m.id == mechanism_id:
            return m
    raise AppError(ErrorCode.NOT_FOUND, f"机制 {mechanism_id} 不存在", 404)
