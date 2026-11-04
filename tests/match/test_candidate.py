"""候选生成：跨域配对与结构/语义打分。"""

from __future__ import annotations

import json

from conceptbridge.common.config import fixture_path
from conceptbridge.common.schemas import (
    ActionRef,
    ConceptRef,
    EvidenceSpan,
    MechanismUnit,
    StructuralSignature,
)
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


def _unit(
    unit_id: str,
    *,
    domain: str = "materials_science",
    subject: str,
    result: str,
) -> MechanismUnit:
    return MechanismUnit(
        id=unit_id,
        paper_id="W1",
        domain=domain,
        subject=ConceptRef(concept_id=f"c_{unit_id}", surface=subject, type="structure"),
        action=ActionRef(verb="promote", action_class="promote", polarity="promote"),
        object=ConceptRef(concept_id=f"o_{unit_id}", surface="outcome", type="process"),
        conditions=[],
        result=result,
        signature=StructuralSignature(
            subject_type="structure",
            action_class="promote",
            object_type="process",
            causality="direct",
            polarity="promote",
            condition_count=0,
            condition_keys=[],
            arity=2,
        ),
        evidence=EvidenceSpan(span=result, section="abstract", char_start=0, char_end=len(result)),
        confidence=0.5,
        extractor_version="test",
    )


def test_subject_term_outranks_result_only_mention() -> None:
    """标题里的术语应压过只出现在结果正文里的偶然词。"""
    fold_only = _unit("fold", subject="nonlinear equations", result="we fold the matrix")
    protein = _unit(
        "protein",
        domain="biology",
        subject="protein anchor site",
        result="binds the ligand",
    )
    matched = select_sources("蛋白质折叠", [fold_only, protein], None)
    assert [item.id for item in matched] == ["protein"]


def test_lithium_surface_ranks_before_generic_dendrite() -> None:
    generic = _unit("generic", subject="dendritic solidification", result="microstructure")
    lithium = _unit("lithium", subject="dendritic electrodeposition of Li metal", result="uniform")
    matched = select_sources("锂枝晶抑制", [generic, lithium], None)
    assert matched[0].id == "lithium"


def test_source_selection_caps_tied_matches_and_fallback() -> None:
    tied = [
        _unit(f"d{index}", subject=f"dendrite sample {index}", result="growth")
        for index in range(8)
    ]
    matched = select_sources("dendrite", tied, None)
    assert len(matched) == 5

    materials = [_unit(f"m{index}", subject=f"alpha {index}", result="beta") for index in range(7)]
    biology = _unit("bio", domain="biology", subject="cell wall", result="stable")
    fallback = select_sources("zzzzqq", [*materials, biology], None)
    assert len(fallback) == 5
    assert {item.domain for item in fallback} == {"materials_science"}


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
