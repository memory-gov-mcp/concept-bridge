"""评测指标：答辩看板直接投屏这个。"""

from __future__ import annotations

import json

from fastapi import APIRouter

from ...common.config import REPO_ROOT
from ...common.schemas import EvalReport

router = APIRouter(tags=["eval"])

_LATEST = REPO_ROOT / "eval" / "reports" / "latest.json"


@router.get("/eval/report", response_model=EvalReport, summary="最新评测报告")
def get_eval_report() -> EvalReport:
    if _LATEST.exists():
        return EvalReport.model_validate(json.loads(_LATEST.read_text(encoding="utf-8")))
    return EvalReport(
        generated_at="1970-01-01T00:00:00Z",
        gold_pairs=0,
        hard_negatives=0,
        rows=[],
        notes="评测尚未生成，运行 uv run task eval 后刷新",
    )
