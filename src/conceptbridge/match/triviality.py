"""反琐碎惩罚。命中任一条即 1，否则 0。最终分在这里夹到 [0, 1]。"""

from __future__ import annotations

from ..common.schemas import StructuralSignature
from .config import FINAL_WEIGHTS, GENERIC_VERBS


def triviality_penalty(
    signature: StructuralSignature,
    *,
    verb: str,
    name_similarity: float = 0.0,
) -> float:
    """条件为空、元数不足、泛化动词或几乎同名，都视为废话桥。"""
    if signature.condition_count == 0 or signature.arity < 2:
        return 1.0
    if any(word in verb for word in GENERIC_VERBS):
        return 1.0
    if name_similarity > 0.95:
        return 1.0
    return 0.0


def final_score(struct: float, semantic: float, domain_dist: float, triviality: float) -> float:
    """0.45*struct + 0.30*sem + 0.25*domain - 0.35*triviality，再夹到 [0, 1]。"""
    raw = (
        FINAL_WEIGHTS["struct"] * struct
        + FINAL_WEIGHTS["semantic"] * semantic
        + FINAL_WEIGHTS["domain"] * domain_dist
        - FINAL_WEIGHTS["triviality"] * triviality
    )
    return min(1.0, max(0.0, raw))
