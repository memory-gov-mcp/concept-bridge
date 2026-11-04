"""候选生成。结构分、语义分、领域距离和反琐碎都在配对时算完。"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from ..common.schemas import BridgeScores, MechanismUnit
from ..graph.embeddings import hash_embed
from .config import domain_distance
from .structural import struct_sim
from .triviality import final_score, triviality_penalty


@dataclass(frozen=True)
class ScoredPair:
    source: MechanismUnit
    target: MechanismUnit
    scores: BridgeScores


def _text(mechanism: MechanismUnit) -> str:
    return " ".join(
        [
            mechanism.subject.surface,
            mechanism.action.verb,
            mechanism.object.surface,
            " ".join(mechanism.conditions),
            mechanism.result,
        ]
    )


@lru_cache(maxsize=8192)
def _vector(text: str) -> np.ndarray:
    return hash_embed([text])[0]


def _cosine(left: str, right: str) -> float:
    return min(1.0, max(0.0, float(np.dot(_vector(left), _vector(right)))))


def score_pair(source: MechanismUnit, target: MechanismUnit) -> BridgeScores:
    structural = struct_sim(source.signature, target.signature)
    semantic = _cosine(
        " ".join([source.action.verb, *source.conditions, source.result]),
        " ".join([target.action.verb, *target.conditions, target.result]),
    )
    distance = domain_distance(source.domain, target.domain)
    triviality = triviality_penalty(
        target.signature,
        verb=target.action.verb,
    )
    if triviality == 0.0:
        name_similarity = max(
            _cosine(source.subject.surface, target.subject.surface),
            _cosine(source.object.surface, target.object.surface),
        )
        triviality = triviality_penalty(
            target.signature, verb=target.action.verb, name_similarity=name_similarity
        )
    return BridgeScores(
        structural=structural,
        semantic=semantic,
        domain_distance=distance,
        triviality=triviality,
        final=final_score(structural, semantic, distance, triviality),
    )


def select_sources(
    query: str,
    mechanisms: list[MechanismUnit],
    source_domain: str | None,
) -> list[MechanismUnit]:
    """有词面重叠就用重叠最高的领域；没有则退回一个仍能跨域的源领域。"""
    if source_domain:
        picked = [item for item in mechanisms if item.domain == source_domain]
        if picked:
            return picked

    def overlap(mechanism: MechanismUnit) -> int:
        text = _text(mechanism)
        return sum(1 for char in query if not char.isspace() and char in text)

    scored = [(overlap(item), item) for item in mechanisms]
    best = max((score for score, _ in scored), default=0)
    if best > 0:
        winners = [item for score, item in scored if score > 0]
        top = max(winners, key=overlap)
        return [item for item in winners if item.domain == top.domain]

    by_domain: dict[str, list[MechanismUnit]] = {}
    for item in mechanisms:
        by_domain.setdefault(item.domain, []).append(item)
    if "materials_science" in by_domain and len(by_domain) > 1:
        return by_domain["materials_science"]
    for domain, group in by_domain.items():
        if any(item.domain != domain for item in mechanisms):
            return group
    return mechanisms[:1]


def rank_candidates(
    sources: list[MechanismUnit],
    mechanisms: list[MechanismUnit],
    *,
    exclude_domains: list[str] | None,
    top_k: int,
) -> tuple[list[ScoredPair], int]:
    """只保留跨域目标。返回去重后的 top-k，以及去重前的候选对数。"""
    excluded = set(exclude_domains or [])
    source_ids = {item.id for item in sources}
    pairs: list[ScoredPair] = []
    for source in sources:
        for target in mechanisms:
            if target.id in source_ids:
                continue
            if target.domain == source.domain or target.domain in excluded:
                continue
            pairs.append(ScoredPair(source, target, score_pair(source, target)))
    pairs.sort(key=lambda item: (-item.scores.final, item.target.id))
    chosen: list[ScoredPair] = []
    seen: set[str] = set()
    for pair in pairs:
        if pair.target.id in seen:
            continue
        seen.add(pair.target.id)
        chosen.append(pair)
        if len(chosen) >= top_k:
            break
    return chosen, len(pairs)
