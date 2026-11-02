"""金标准闭集上的消融。指标只来自当次打分，不写死。

语料是正例材料化出的机制，不是文献全库。负例不进入命中集。
重排在没有 LLM 缓存时不改变分数，调用方仍传入 use_rerank 以保留四行消融。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ..common.config import REPO_ROOT
from ..common.schemas import (
    ActionRef,
    ConceptRef,
    EvidenceSpan,
    MechanismUnit,
    StructuralSignature,
)
from .candidate import score_pair
from .triviality import final_score

GOLD_PATH = REPO_ROOT / "eval" / "gold" / "analogy_pairs.jsonl"
REPORTS = REPO_ROOT / "eval" / "reports"

ABLATIONS: tuple[tuple[str, bool, bool, bool], ...] = (
    ("A 纯语义(baseline)", False, False, False),
    ("B +结构签名", True, False, False),
    ("C +领域距离", True, True, False),
    ("D 完整", True, True, True),
)

_TYPES = {"structure", "process", "substance", "signal", "state"}
_ACTIONS = {
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
}
_CAUSAL = {"direct", "mediated", "feedback", "threshold"}
_POLAR = {"promote", "inhibit", "neutral"}


def parse_shared_structure(text: str) -> tuple[str, str, str, str, str]:
    """解析 `类型→动作→类型 | 因果 | 极性`。"""
    try:
        left, causality, polarity = (part.strip() for part in text.split("|"))
        subject_type, action, object_type = (part.strip() for part in left.split("→"))
    except ValueError as exc:
        raise ValueError(f"无法解析 shared_structure: {text}") from exc
    if subject_type not in _TYPES or object_type not in _TYPES:
        raise ValueError(f"概念类型不在枚举内: {text}")
    if action not in _ACTIONS or causality not in _CAUSAL or polarity not in _POLAR:
        raise ValueError(f"动作或因果不在枚举内: {text}")
    return subject_type, action, object_type, causality, polarity


def ablation_score(
    source: MechanismUnit,
    target: MechanismUnit,
    *,
    use_struct: bool,
    use_domain: bool,
    use_rerank: bool,
) -> float:
    """按消融开关组合最终分。use_rerank 不改数值，只保留与文案重排对齐的开关。"""
    del use_rerank
    scored = score_pair(source, target)
    return final_score(
        scored.structural if use_struct else 0.0,
        scored.semantic,
        scored.domain_distance if use_domain else 0.0,
        scored.triviality,
    )


def hit_rate(ranks: list[int], *, cutoff: int) -> float:
    if not ranks:
        return 0.0
    return sum(1 for rank in ranks if rank <= cutoff) / len(ranks)


def mean_reciprocal_rank(ranks: list[int], *, cutoff: int) -> float:
    if not ranks:
        return 0.0
    total = sum(1.0 / rank for rank in ranks if rank <= cutoff)
    return total / len(ranks)


def load_gold(path: Path = GOLD_PATH) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def materialize(row: dict, role: str) -> MechanismUnit:
    subject_type, action, object_type, causality, polarity = parse_shared_structure(row["shared_structure"])
    prose = str(row["source_mechanism"] if role == "source" else row["target_mechanism"]).strip()
    if not prose:
        prose = row["shared_structure"]
    span = prose[:400]
    prefix = f"{row['id']}_{role}"
    domain = row["source_domain"] if role == "source" else row["target_domain"]
    return MechanismUnit(
        id=prefix,
        paper_id=f"gold_{prefix}",
        domain=domain,
        subject=ConceptRef(concept_id=f"c_{prefix}_s", surface=prose[:24], type=subject_type),
        action=ActionRef(verb=action, action_class=action, polarity=polarity),
        object=ConceptRef(concept_id=f"c_{prefix}_o", surface=prose[-24:], type=object_type),
        conditions=["gold_pair"],
        result=prose,
        signature=StructuralSignature(
            subject_type=subject_type,
            action_class=action,
            object_type=object_type,
            causality=causality,
            polarity=polarity,
            condition_count=1,
            condition_keys=["gold_pair"],
            arity=2,
        ),
        evidence=EvidenceSpan(span=span, section="abstract", char_start=0, char_end=len(span)),
        confidence=0.5,
        extractor_version="gold-v1",
    )


def materialize_negative(row: dict, role: str) -> MechanismUnit:
    """负例没有 shared_structure。用泛化动词和空条件，让惩罚项能被算出来。"""
    prose = str(row["source_mechanism"] if role == "source" else row["target_mechanism"]).strip() or "泛化属性"
    span = prose[:400]
    prefix = f"{row['id']}_{role}"
    domain = row["source_domain"] if role == "source" else row["target_domain"]
    return MechanismUnit(
        id=prefix,
        paper_id=f"gold_{prefix}",
        domain=domain,
        subject=ConceptRef(concept_id=f"c_{prefix}_s", surface=prose[:24], type="process"),
        action=ActionRef(verb="相关", action_class="promote", polarity="neutral"),
        object=ConceptRef(concept_id=f"c_{prefix}_o", surface=prose[-24:], type="process"),
        conditions=[],
        result=prose,
        signature=StructuralSignature(
            subject_type="process",
            action_class="promote",
            object_type="process",
            causality="direct",
            polarity="neutral",
            condition_count=0,
            condition_keys=[],
            arity=2,
        ),
        evidence=EvidenceSpan(span=span, section="abstract", char_start=0, char_end=len(span)),
        confidence=0.5,
        extractor_version="gold-v1",
    )


def _ranks(
    pairs: list[tuple[MechanismUnit, str]],
    targets: list[MechanismUnit],
    flags: tuple[bool, bool, bool],
) -> list[int]:
    use_struct, use_domain, use_rerank = flags
    ranks: list[int] = []
    for source, relevant_id in pairs:
        order = sorted(
            targets,
            key=lambda target: (
                -ablation_score(
                    source,
                    target,
                    use_struct=use_struct,
                    use_domain=use_domain,
                    use_rerank=use_rerank,
                ),
                target.id,
            ),
        )
        ranks.append(next(index for index, target in enumerate(order, start=1) if target.id == relevant_id))
    return ranks


def _trivial_copy(target: MechanismUnit) -> MechanismUnit:
    data = target.model_dump()
    data["action"]["verb"] = "促进"
    data["conditions"] = []
    data["signature"]["condition_count"] = 0
    data["signature"]["condition_keys"] = []
    return MechanismUnit.model_validate(data)


def build_report(rows: list[dict] | None = None) -> dict:
    gold = rows if rows is not None else load_gold()
    positives = [row for row in gold if str(row.get("id", "")).startswith("g")]
    negatives = [row for row in gold if str(row.get("id", "")).startswith("n")]
    pairs = [(materialize(row, "source"), f"{row['id']}_target", row) for row in positives]
    targets = [materialize(row, "target") for row in positives]
    ranking_pairs = [(source, relevant) for source, relevant, _row in pairs]

    metric_rows = []
    full_ranks: list[int] = []
    for name, use_struct, use_domain, use_rerank in ABLATIONS:
        flags = (use_struct, use_domain, use_rerank)
        ranks = _ranks(ranking_pairs, targets, flags)
        if use_struct and use_domain and use_rerank:
            full_ranks = ranks
        metric_rows.append(
            {
                "config": name,
                "use_structural": use_struct,
                "use_domain_distance": use_domain,
                "use_rerank": use_rerank,
                "p_at_5": round(hit_rate(ranks, cutoff=5), 6),
                "mrr_at_10": round(mean_reciprocal_rank(ranks, cutoff=10), 6),
            }
        )

    success_index = max(
        range(len(pairs)),
        key=lambda index: ablation_score(
            pairs[index][0],
            targets[index],
            use_struct=True,
            use_domain=True,
            use_rerank=True,
        ),
        default=0,
    )
    success_source, _relevant, success_row = pairs[success_index]
    success_target = targets[success_index]
    success_score = score_pair(success_source, success_target)
    trivial_target = _trivial_copy(success_target)
    trivial_score = score_pair(success_source, trivial_target)

    negative = negatives[0] if negatives else None
    negative_score = None
    if negative is not None:
        negative_score = score_pair(
            materialize_negative(negative, "source"),
            materialize_negative(negative, "target"),
        )

    b_row, c_row, d_row = metric_rows[1], metric_rows[2], metric_rows[3]
    notes = [
        "语料是金标准正例材料化成的机制闭集，不是 1500 篇文献库。",
        "P@5 是正确目标出现在前 5 名的查询占比；负例不进入命中集。",
    ]
    if b_row["p_at_5"] == c_row["p_at_5"] and b_row["mrr_at_10"] == c_row["mrr_at_10"]:
        notes.append("闭集中目标全部跨 field，domain_dist 恒为 1，B 与 C 的排序相同。")
    if c_row["p_at_5"] == d_row["p_at_5"] and c_row["mrr_at_10"] == d_row["mrr_at_10"]:
        notes.append("重排只在 LLM 缓存命中时改写文案，不改变分数，因此无缓存时 D 与 C 相同。")

    case_ids = [str(success_row["id"]), f"{success_row['id']}:trivial", str(negative["id"]) if negative else "n/a"]
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gold_pairs": len(positives),
        "hard_negatives": len(negatives),
        "kappa": None,
        "rows": metric_rows,
        "case_study_ids": case_ids,
        "notes": "".join(notes),
        "cases": {
            "success": {
                "id": success_row["id"],
                "query": success_row.get("query", ""),
                "rank": full_ranks[success_index] if full_ranks else None,
                "final": success_score.final,
                "structural": success_score.structural,
                "semantic": success_score.semantic,
                "triviality": success_score.triviality,
            },
            "trivial": {
                "id": f"{success_row['id']}:trivial",
                "verb": "促进",
                "final": trivial_score.final,
                "triviality": trivial_score.triviality,
                "baseline_final": success_score.final,
            },
            "negative": None
            if negative is None or negative_score is None
            else {
                "id": negative["id"],
                "why_invalid": negative.get("why_invalid", ""),
                "trap_type": negative.get("trap_type", ""),
                "final": negative_score.final,
                "triviality": negative_score.triviality,
            },
        },
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# 评测报告",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 正例：{report['gold_pairs']} ｜ 负例：{report['hard_negatives']}",
        f"- 说明：{report['notes']}",
        "",
        "| 配置 | struct | domain | rerank | P@5 | MRR@10 |",
        "|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['config']} | {row['use_structural']} | {row['use_domain_distance']} "
            f"| {row['use_rerank']} | {row['p_at_5']:.4f} | {row['mrr_at_10']:.4f} |"
        )
    success = report["cases"]["success"]
    trivial = report["cases"]["trivial"]
    negative = report["cases"]["negative"]
    lines.extend(
        [
            "",
            "## Case studies",
            "",
            f"- 高分正例 `{success['id']}`（{success['query']}）："
            f"rank={success['rank']} structural={success['structural']:.4f} "
            f"semantic={success['semantic']:.4f} final={success['final']:.4f}",
            f"- 反琐碎 `{trivial['id']}`：把动词改成「{trivial['verb']}」并清空条件后 "
            f"triviality={trivial['triviality']:.1f}，final 从 {trivial['baseline_final']:.4f} "
            f"降到 {trivial['final']:.4f}",
        ]
    )
    if negative is not None:
        lines.append(
            f"- 负例 `{negative['id']}`（{negative['trap_type']}）："
            f"triviality={negative['triviality']:.1f} final={negative['final']:.4f}。"
            f"{negative['why_invalid']}"
        )
    return "\n".join(lines) + "\n"


def write_reports(report: dict, directory: Path = REPORTS) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    public = {key: value for key, value in report.items() if key != "cases"}
    (directory / "latest.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (directory / "latest.md").write_text(render_markdown(report), encoding="utf-8")


def main(directory: Path | None = None) -> int:
    report = build_report()
    write_reports(report, directory or REPORTS)
    print(f"gold={report['gold_pairs']}P/{report['hard_negatives']}N -> eval/reports/latest.json")
    for row in report["rows"]:
        print(f"{row['config']} P@5={row['p_at_5']:.4f} MRR@10={row['mrr_at_10']:.4f}")
    return 0
