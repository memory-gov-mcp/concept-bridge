"""重排只读缓存。未命中时退回规则文案，引用仍是 evidence.span。"""

from __future__ import annotations

import json

from conceptbridge.common.config import fixture_path
from conceptbridge.common.llm import LLMClient
from conceptbridge.common.schemas import MechanismUnit
from conceptbridge.match.explain import explain_bridge
from conceptbridge.match.rerank import rerank_explanation, rerank_payload


def _load(mechanism_id: str) -> MechanismUnit:
    raw = json.loads(fixture_path("bridge.sample.json").read_text(encoding="utf-8"))
    rows = list(raw["source"]["mechanisms"])
    rows.extend(bridge["target_mechanism"] for bridge in raw["bridges"])
    return MechanismUnit.model_validate(next(item for item in rows if item["id"] == mechanism_id))


def test_cache_miss_keeps_rule_text_and_span(tmp_path, monkeypatch) -> None:
    def explode(*_args, **_kwargs):
        raise AssertionError("重排不应发起网络请求")

    monkeypatch.setattr(LLMClient, "_post", explode)
    client = LLMClient(cache_dir=tmp_path)
    source, target = _load("mu_01J9A2K7"), _load("mu_01J9B001")
    explained = rerank_explanation(source, target, client=client)
    rule = explain_bridge(source, target)
    assert explained.hypothesis == rule.hypothesis
    assert explained.differences == rule.differences
    assert explained.citations[0].span == target.evidence.span


def test_cache_hit_replaces_wording_only(tmp_path) -> None:
    client = LLMClient(cache_dir=tmp_path)
    source, target = _load("mu_01J9A2K7"), _load("mu_01J9B001")
    payload = rerank_payload(source, target, client.settings)
    client.write_cache(
        client.cache_key(payload),
        {"transferable_hypothesis": "缓存里的可迁移假设", "differences": ["尺度不同"]},
    )
    explained = rerank_explanation(source, target, client=client)
    assert explained.hypothesis == "缓存里的可迁移假设"
    assert explained.differences == ["尺度不同"]
    assert explained.citations[0].span == target.evidence.span
    assert explained.citations[0].char_start == target.evidence.char_start


def test_malformed_cache_falls_back(tmp_path) -> None:
    client = LLMClient(cache_dir=tmp_path)
    source, target = _load("mu_01J9A2K7"), _load("mu_01J9B001")
    payload = rerank_payload(source, target, client.settings)
    client.write_cache(client.cache_key(payload), {"transferable_hypothesis": ""})
    explained = rerank_explanation(source, target, client=client)
    assert explained.hypothesis == explain_bridge(source, target).hypothesis
    assert explained.citations
