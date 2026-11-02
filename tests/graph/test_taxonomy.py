"""12 类动作词典。未命中返回 None，不调用 LLM。"""

from __future__ import annotations

from conceptbridge.graph.taxonomy import CLASSIFY_ACTIONS, classify_action


def test_each_class_has_a_verb() -> None:
    assert len(CLASSIFY_ACTIONS) == 12
    for action in CLASSIFY_ACTIONS:
        assert classify_action(action) == action


def test_surface_aliases_and_non_verbs() -> None:
    assert classify_action("selectively_transport") == "transport"
    assert classify_action("抑制") == "inhibit"
    assert classify_action("膜") is None
    assert classify_action("细胞膜") is None
    assert classify_action("unknown_verb") is None
