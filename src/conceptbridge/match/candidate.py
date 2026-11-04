"""候选生成。结构分、语义分、领域距离和反琐碎都在配对时算完。"""

from __future__ import annotations

import math
import re
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


# --------------------------------------------------------------------------- #
# 查询 → 源机制定位
#
# 原先按"单个字符"统计重叠，对英文语料完全失效：p/r/o/t/e/n 这类字母几乎每个机制
# 文本里都有，于是任何英文查询都能命中大半个语料，最后等于随机挑一个领域；
# 中文查询在英文语料上更是零命中，直接落到"返回整个领域"的兜底。
# 现在改成：ASCII 查询按**整词**匹配；中文查询先查术语表映射成英文词，
# 映射不到再退回中文字符二元组（这样中文 fixture 仍然能选源）。
# --------------------------------------------------------------------------- #

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-]{1,}", re.IGNORECASE)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# 演示与常见术语的中→英映射。只为让中文查询能在英文语料上定位源机制，
# 不做通用翻译；真正的跨语言检索应交给多语种向量（见 AGENTS.md 的待办）。
_CN_TERMS: dict[str, tuple[str, ...]] = {
    "锂枝晶": ("dendrite", "dendritic"),
    "枝晶": ("dendrite", "dendritic"),
    "催化剂": ("catalyst", "catalytic"),
    "催化": ("catalyst", "catalytic"),
    "失活": ("deactivation", "deactivate"),
    "蛋白质": ("protein",),
    "折叠": ("folding", "fold"),
    "电池": ("battery",),
    "电解质": ("electrolyte",),
    "电极": ("electrode",),
    "膜": ("membrane", "film"),
    "离子": ("ion",),
    "扩散": ("diffusion",),
    "腐蚀": ("corrosion",),
    "合金": ("alloy",),
    "免疫": ("immune",),
    "酶": ("enzyme",),
    "细胞": ("cell",),
    "热失控": ("thermal", "runaway"),
}
# 注意：**不要**把「抑制/促进/提高」这类泛化动作词放进表里。
# fixture 里生物机制的动词就是 suppress，一旦映射过去，中文查询会把生物领域误判成源。


def _ascii_words(text: str) -> set[str]:
    return {word.lower() for word in _WORD_RE.findall(text)}


def _cn_terms(query: str) -> set[str]:
    terms: set[str] = set()
    for chinese, english in _CN_TERMS.items():
        if chinese in query:
            terms.update(english)
    return terms


def _cjk_grams(query: str) -> set[str]:
    chars = "".join(_CJK_RE.findall(query))
    grams = set(chars)
    grams.update(chars[i : i + 2] for i in range(len(chars) - 1))
    return {gram for gram in grams if gram}


def _query_mode(query: str) -> tuple[str, set[str]]:
    """把查询归一成 (匹配模式, 词元集合)。

    - word: ASCII 词元（英文查询）或术语表映射（中文查询）
    - char: 中文字符组（中文语料、无映射时兜底）
    """
    words = _ascii_words(query)
    if words:
        return "word", words
    mapped = _cn_terms(query)
    if mapped:
        return "word", mapped
    return "char", _cjk_grams(query)


def _score_chars(
    tokens: set[str], mechanisms: list[MechanismUnit]
) -> list[tuple[float, MechanismUnit]]:
    """中文语料路径：按字符组出现在原文里的个数打分。"""
    return [
        (float(sum(1 for gram in tokens if gram in _text(item))), item) for item in mechanisms
    ]


def _score_words(
    tokens: set[str], mechanisms: list[MechanismUnit]
) -> list[tuple[float, MechanismUnit]]:
    """IDF 加权词面打分，压掉 li / inhibit 这类到处都有的泛词。"""
    word_sets = [_ascii_words(_text(item)) for item in mechanisms]
    df: dict[str, int] = {}
    for words in word_sets:
        for word in words:
            df[word] = df.get(word, 0) + 1
    total = max(1, len(mechanisms))
    weights = {token: math.log((total + 1) / (df.get(token, 0) + 1)) + 1.0 for token in tokens}
    return [
        (sum(weight for token, weight in weights.items() if token in words), item)
        for item, words in zip(mechanisms, word_sets, strict=True)
    ]


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

    mode, tokens = _query_mode(query)
    if not tokens:
        scored: list[tuple[float, MechanismUnit]] = [(0.0, item) for item in mechanisms]
    elif mode == "char":
        scored = _score_chars(tokens, mechanisms)
    else:
        scored = _score_words(tokens, mechanisms)
        # 中文查询映射成了英文词，但语料本身是中文（fixture）时，词面必然零命中，
        # 这时退回中文字符匹配，否则会一路掉到"返回整个领域"的兜底。
        if max((score for score, _ in scored), default=0.0) <= 0 and _CJK_RE.search(query):
            scored = _score_chars(_cjk_grams(query), mechanisms)

    best_score = max((score for score, _ in scored), default=0.0)
    if best_score > 0:
        # 只取最高分档：原先的 `> 0` 会把一个弱命中拖进整个领域（中文查询返回 92 条就是这么来的）
        winners = [item for score, item in scored if score >= best_score - 1e-9]
        counts: dict[str, int] = {}
        for item in winners:
            counts[item.domain] = counts.get(item.domain, 0) + 1
        top_domain = max(counts, key=lambda name: counts[name])
        return [item for item in winners if item.domain == top_domain]

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
