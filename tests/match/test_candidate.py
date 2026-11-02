"""候选生成：跨域配对与结构/语义打分。"""

from __future__ import annotations

import json

from conceptbridge.common.config import fixture_path
from conceptbridge.common.schemas import MechanismUnit
from conceptbridge.match.candidate import rank_candidates, score_pair, select_sources


def load_fixture_mechanisms() -> list[MechanismUnit]:
    raw = json.loads(fixture_path("bridge.sample.json").read_text(encoding="utf-8"))
    units = [MechanismUnit.model_validate(item) for item in raw["source"]["mechanisms"]]
    units.extend(
        MechanismUnit.model_validate(bridge["target_mechanism"]) for bridge in raw["bridges"]
    )
    return units


def test_structural_transport_pair_is_cross_domain() -> None:
    mechanisms = load_fixture_mechanisms()
    source = next(item for item in mechanisms if item.id == "mu_01J9A2K7")
    target = next(item for item in mechanisms if item.id == "mu_01J9B001")
    scores = score_pair(source, target)
    assert scores.domain_distance == 1.0
    assert scores.triviality == 0.0
    assert scores.structural > 0.8
    assert 0.0 <= scores.final <= 1.0


def test_query_selects_matching_domain_and_fallback_stays_nonempty() -> None:
    mechanisms = load_fixture_mechanisms()
    matched = select_sources("锂枝晶抑制", mechanisms, None)
    assert matched
    assert {item.domain for item in matched} == {"materials_science"}
    fallback = select_sources("蛋白质折叠", mechanisms, None)
    assert fallback
    assert any(item.domain != fallback[0].domain for item in mechanisms)


def test_rank_respects_top_k_and_exclude() -> None:
    mechanisms = load_fixture_mechanisms()
    sources = select_sources("锂枝晶抑制", mechanisms, None)
    excluded, excluded_count = rank_candidates(
        sources, mechanisms, exclude_domains=["biology"], top_k=5
    )
    assert excluded == []
    assert excluded_count == 0
    ranked, count = rank_candidates(sources, mechanisms, exclude_domains=[], top_k=1)
    assert len(ranked) == 1
    assert count >= len(ranked)
    assert ranked[0].target.domain != sources[0].domain
