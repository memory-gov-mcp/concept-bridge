"""结构打分与反琐碎。权重以 AGENTS.md §5.3 为准。"""

from __future__ import annotations

from conceptbridge.common.schemas import StructuralSignature
from conceptbridge.match.config import FINAL_WEIGHTS, STRUCT_WEIGHTS, domain_distance
from conceptbridge.match.structural import struct_sim


def test_struct_weights_match_spec() -> None:
    assert STRUCT_WEIGHTS == {
        "role_type": 0.30,
        "action_class": 0.25,
        "causality": 0.15,
        "condition": 0.15,
        "polarity": 0.15,
    }
    assert abs(sum(STRUCT_WEIGHTS.values()) - 1.0) < 1e-9


def test_final_weights_match_spec() -> None:
    assert FINAL_WEIGHTS["struct"] == 0.45
    assert FINAL_WEIGHTS["semantic"] == 0.30
    assert FINAL_WEIGHTS["domain"] == 0.25
    assert FINAL_WEIGHTS["triviality"] == 0.35


def _sig(**overrides: object) -> StructuralSignature:
    base: dict[str, object] = {
        "subject_type": "structure",
        "action_class": "transport",
        "object_type": "process",
        "causality": "direct",
        "polarity": "neutral",
        "condition_count": 2,
        "condition_keys": ["concentration_gradient", "electric_field"],
        "arity": 2,
    }
    base.update(overrides)
    return StructuralSignature.model_validate(base)


def test_identical_signature_scores_one() -> None:
    sig = _sig()
    assert struct_sim(sig, sig) == 1.0


def test_action_class_mismatch_drops_its_weight() -> None:
    left = _sig()
    right = _sig(action_class="inhibit")
    assert abs(struct_sim(left, right) - 0.75) < 1e-9


def test_domain_distance_is_zero_only_inside_one_field() -> None:
    assert domain_distance("materials_science", "materials_science") == 0.0
    assert domain_distance("materials", "materials_science") == 0.0
    assert domain_distance("materials_science", "biology") == 1.0
    assert domain_distance("chemistry", "biology") == 1.0
