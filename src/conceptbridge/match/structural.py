"""结构签名相似度。五项权重来自 match.config，这里只做匹配。"""

from __future__ import annotations

from ..common.schemas import StructuralSignature
from .config import STRUCT_WEIGHTS


def _jaccard(left: list[str], right: list[str]) -> float:
    a, b = set(left), set(right)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def struct_sim(left: StructuralSignature, right: StructuralSignature) -> float:
    """主客体类型、动作、因果、条件、极性的加权匹配，范围 [0, 1]。"""
    role = float(
        left.subject_type == right.subject_type and left.object_type == right.object_type
    )
    parts = {
        "role_type": role,
        "action_class": float(left.action_class == right.action_class),
        "causality": float(left.causality == right.causality),
        "condition": _jaccard(left.condition_keys, right.condition_keys),
        "polarity": float(left.polarity == right.polarity),
    }
    return sum(STRUCT_WEIGHTS[name] * value for name, value in parts.items())
