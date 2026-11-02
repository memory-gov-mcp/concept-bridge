"""规则解释：假设、差异、对齐和引用都挂在目标机制的 evidence 上。"""

from __future__ import annotations

import json

from conceptbridge.common.config import fixture_path
from conceptbridge.common.schemas import MechanismUnit
from conceptbridge.match.explain import explain_bridge


def _load(mechanism_id: str) -> MechanismUnit:
    raw = json.loads(fixture_path("bridge.sample.json").read_text(encoding="utf-8"))
    rows = list(raw["source"]["mechanisms"])
    rows.extend(bridge["target_mechanism"] for bridge in raw["bridges"])
    return MechanismUnit.model_validate(next(item for item in rows if item["id"] == mechanism_id))


def test_explanation_cites_target_evidence() -> None:
    source = _load("mu_01J9A2K7")
    target = _load("mu_01J9B001")
    explained = explain_bridge(source, target)
    assert explained.hypothesis
    assert explained.differences
    assert {item.source_role for item in explained.alignment} >= {"subject", "object"}
    assert explained.citations
    citation = explained.citations[0]
    assert citation.paper_id == target.paper_id
    assert citation.span == target.evidence.span
    assert citation.char_start == target.evidence.char_start
    assert citation.char_end == target.evidence.char_end
