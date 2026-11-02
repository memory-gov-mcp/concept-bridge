"""12 类动作词典。未命中返回 None；本模块不调用 LLM。"""

from __future__ import annotations

from ..common.schemas import ActionClass

CLASSIFY_ACTIONS: tuple[ActionClass, ...] = (
    "inhibit",
    "promote",
    "transport",
    "transform",
    "recognize",
    "amplify",
    "stabilize",
    "degrade",
    "compete",
    "isolate",
    "trigger",
    "regulate",
)

# 类别名本身也是动词，方便直接吃 action_class 字符串。别名只收明确动词。
_EXACT: dict[str, ActionClass] = {name: name for name in CLASSIFY_ACTIONS}
_EXACT.update(
    {
        "selectively_transport": "transport",
        "抑制": "inhibit",
        "阻断": "inhibit",
        "促进": "promote",
        "运输": "transport",
        "输送": "transport",
        "转化": "transform",
        "识别": "recognize",
        "放大": "amplify",
        "稳定": "stabilize",
        "降解": "degrade",
        "竞争": "compete",
        "隔离": "isolate",
        "触发": "trigger",
        "调节": "regulate",
    }
)


def classify_action(verb: str) -> ActionClass | None:
    """只看动词。概念名如「膜」「细胞膜」不在词表里，返回 None。"""
    key = verb.strip().lower().replace(" ", "_").replace("-", "_")
    if not key:
        return None
    if key in _EXACT:
        return _EXACT[key]
    contained = [
        (len(token), action)
        for token, action in _EXACT.items()
        if len(token) >= 4 and token in key
    ]
    if not contained:
        return None
    contained.sort(reverse=True)
    return contained[0][1]
