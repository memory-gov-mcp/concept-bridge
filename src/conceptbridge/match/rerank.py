"""重排只读 LLM 缓存。未命中、空字段或 DEMO 都不会发请求，退回规则文案。"""

from __future__ import annotations

import json

from ..common.config import Settings
from ..common.llm import LLMClient
from ..common.schemas import MechanismUnit
from .explain import Explanation, explain_bridge

_SYSTEM = "根据两条机制写可迁移假设和差异。引用由系统从 evidence.span 填入，不要编造出处。"


def rerank_payload(source: MechanismUnit, target: MechanismUnit, settings: Settings) -> dict:
    """与 LLMClient.complete_json 使用同一套键，缓存才能对上。"""
    user = json.dumps(
        {"source": source.model_dump(), "target": target.model_dump()},
        ensure_ascii=False,
        sort_keys=True,
    )
    return {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,
        "max_tokens": 512,
        "response_format": {"type": "json_object"},
    }


def _from_cache(hit: dict) -> tuple[str, list[str]] | None:
    hypothesis = hit.get("transferable_hypothesis")
    differences = hit.get("differences")
    if not isinstance(hypothesis, str) or not hypothesis.strip():
        return None
    if not isinstance(differences, list) or not differences:
        return None
    cleaned: list[str] = []
    for item in differences:
        if not isinstance(item, str) or not item.strip():
            return None
        cleaned.append(item.strip())
    return hypothesis.strip(), cleaned


def rerank_explanation(
    source: MechanismUnit,
    target: MechanismUnit,
    *,
    client: LLMClient | None = None,
) -> Explanation:
    rule = explain_bridge(source, target)
    llm = client or LLMClient()
    hit = llm.read_cache(llm.cache_key(rerank_payload(source, target, llm.settings)))
    if not isinstance(hit, dict):
        return rule
    parsed = _from_cache(hit)
    if parsed is None:
        return rule
    hypothesis, differences = parsed
    return Explanation(hypothesis, differences, rule.citations, rule.alignment)
