"""演示期收集"这条桥有没有用"，不参与评分，只用来现场讲故事。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter

from ...common.config import get_settings
from ...common.schemas import FeedbackRequest

router = APIRouter(tags=["feedback"])


@router.post("/feedback", summary="桥是否有用")
def submit_feedback(req: FeedbackRequest) -> dict[str, str]:
    settings = get_settings()
    path = settings.resolved_data_dir / "feedback.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = req.model_dump()
    record["created_at"] = datetime.now(UTC).isoformat()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"status": "recorded"}
