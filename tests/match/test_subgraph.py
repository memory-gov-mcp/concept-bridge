"""多步子图：8 个节点以内走 VF2 或近似编辑距离，超出则退回单条机制。"""

from __future__ import annotations

import time

from conceptbridge.common.schemas import (
    ActionRef,
    ConceptRef,
    EvidenceSpan,
    MechanismUnit,
    StructuralSignature,
)
from conceptbridge.match.subgraph import NODE_LIMIT, match_subgraphs


def _unit(index: int, *, action: str = "transport") -> MechanismUnit:
    subject = f"c_{index}"
    target = f"c_{index + 1}"
    return MechanismUnit(
        id=f"mu_{index}",
        paper_id="W1",
        domain="materials_science",
        subject=ConceptRef(concept_id=subject, surface=subject, type="structure"),
        action=ActionRef(verb=action, action_class=action, polarity="neutral"),
        object=ConceptRef(concept_id=target, surface=target, type="process"),
        conditions=["gold_pair"],
        result="沿边传递",
        signature=StructuralSignature(
            subject_type="structure",
            action_class=action,
            object_type="process",
            causality="direct",
            polarity="neutral",
            condition_count=1,
            condition_keys=["gold_pair"],
            arity=2,
        ),
        evidence=EvidenceSpan(span="沿边传递", section="abstract", char_start=0, char_end=4),
        confidence=0.5,
        extractor_version="test",
    )


def _chain(count: int, *, action: str = "transport", id_offset: int = 0) -> list[MechanismUnit]:
    units = []
    for index in range(count):
        unit = _unit(index + id_offset, action=action)
        units.append(unit)
    return units


def test_isomorphic_pair_uses_vf2() -> None:
    source = _chain(1)
    target = _chain(1, id_offset=100)
    found = match_subgraphs(source, target)
    assert found.mode == "vf2"
    assert found.degraded is False
    assert found.distance == 0.0


def test_action_mismatch_uses_approximate_ged() -> None:
    source = _chain(1, action="transport")
    target = _chain(1, action="inhibit", id_offset=100)
    found = match_subgraphs(source, target)
    assert found.mode == "ged"
    assert found.degraded is False
    assert found.distance > 0.0


def test_over_node_limit_degrades_to_one_triple() -> None:
    count = NODE_LIMIT
    source = _chain(count)
    target = _chain(count, id_offset=100)
    started = time.perf_counter()
    found = match_subgraphs(source, target)
    elapsed = time.perf_counter() - started
    assert found.mode == "triple"
    assert found.degraded is True
    assert found.source_mechanism_id == source[0].id
    assert found.target_mechanism_id == target[0].id
    assert elapsed < 0.5
