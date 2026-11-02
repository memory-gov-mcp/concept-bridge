"""结构打分与反琐碎。权重以 AGENTS.md §5.3 为准。"""

from __future__ import annotations

from conceptbridge.match.config import FINAL_WEIGHTS, STRUCT_WEIGHTS, domain_distance


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


def test_domain_distance_is_zero_only_inside_one_field() -> None:
    assert domain_distance("materials_science", "materials_science") == 0.0
    assert domain_distance("materials", "materials_science") == 0.0
    assert domain_distance("materials_science", "biology") == 1.0
    assert domain_distance("chemistry", "biology") == 1.0
