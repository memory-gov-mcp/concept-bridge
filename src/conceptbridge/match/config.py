"""打分权重与领域距离。数字只放这里，调用方不许再写魔数。

公式见 AGENTS.md §5.3。domain_dist：同一 OpenAlex field 为 0，跨 field 为 1。
公式里的 0.25 就是「跨 domain 加权」，不再在距离内部乘第二层系数。
"""

from __future__ import annotations

STRUCT_WEIGHTS: dict[str, float] = {
    "role_type": 0.30,
    "action_class": 0.25,
    "causality": 0.15,
    "condition": 0.15,
    "polarity": 0.15,
}

FINAL_WEIGHTS: dict[str, float] = {
    "struct": 0.45,
    "semantic": 0.30,
    "domain": 0.25,
    "triviality": 0.35,
}

# 表面动词命中即记琐碎。不按 ActionClass 惩罚，避免合法的 promote 被一刀切。
GENERIC_VERBS: frozenset[str] = frozenset({"影响", "促进", "相关", "参与"})

# 别名收成同一个 field。未列出的标签按原字符串比较。
_FIELD_OF: dict[str, str] = {
    "materials": "materials_science",
    "materials_science": "materials_science",
    "chemistry": "chemistry",
    "biology": "biology",
    "medicine": "medicine",
    "physics": "physics",
    "computer_science": "computer_science",
    "algorithms": "computer_science",
}


def domain_distance(source: str, target: str) -> float:
    """同 field 返回 0，跨 field 返回 1。"""
    left = _FIELD_OF.get(source, source)
    right = _FIELD_OF.get(target, target)
    return 0.0 if left == right else 1.0
