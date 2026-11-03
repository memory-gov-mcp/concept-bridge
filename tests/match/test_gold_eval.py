"""金标准闭集上的消融指标。"""

from __future__ import annotations

import json

from conceptbridge.common.config import fixture_path
from conceptbridge.common.schemas import EvalReport, MechanismUnit
from conceptbridge.match.candidate import score_pair
from conceptbridge.match.gold_eval import (
    ablation_score,
    build_report,
    hard_negative_rates,
    hit_rate,
    main,
    mean_reciprocal_rank,
    parse_shared_structure,
)
from conceptbridge.match.triviality import final_score


def _fixture_pair() -> tuple[MechanismUnit, MechanismUnit]:
    raw = json.loads(fixture_path("bridge.sample.json").read_text(encoding="utf-8"))
    source = MechanismUnit.model_validate(raw["source"]["mechanisms"][0])
    target = MechanismUnit.model_validate(raw["bridges"][0]["target_mechanism"])
    return source, target


def test_parse_shared_structure() -> None:
    assert parse_shared_structure("structure→stabilize→structure | direct | promote") == (
        "structure",
        "stabilize",
        "structure",
        "direct",
        "promote",
    )


def test_ablation_drops_disabled_terms() -> None:
    source, target = _fixture_pair()
    scored = score_pair(source, target)
    full = ablation_score(source, target, use_struct=True, use_domain=True, use_rerank=True)
    no_domain = ablation_score(source, target, use_struct=True, use_domain=False, use_rerank=False)
    semantic_only = ablation_score(source, target, use_struct=False, use_domain=False, use_rerank=False)
    assert abs(full - final_score(scored.structural, scored.semantic, scored.domain_distance, scored.triviality)) < 1e-9
    assert abs(no_domain - final_score(scored.structural, scored.semantic, 0.0, scored.triviality)) < 1e-9
    assert abs(semantic_only - final_score(0.0, scored.semantic, 0.0, scored.triviality)) < 1e-9
    assert full == ablation_score(source, target, use_struct=True, use_domain=True, use_rerank=False)


def test_hit_rate_and_mrr() -> None:
    assert hit_rate([1, 6, 5], cutoff=5) == 2 / 3
    assert mean_reciprocal_rank([1, 11], cutoff=10) == 0.5


def test_hard_negative_false_positive_rate_drops() -> None:
    rates = hard_negative_rates()
    assert rates.count == 10
    assert rates.full < rates.without_triviality
    report = build_report()
    assert "误报率" in (report["notes"] or "")
    assert f"{rates.without_triviality:.4f}" in report["notes"]
    assert f"{rates.full:.4f}" in report["notes"]


def test_eval_report_is_computed(tmp_path, capsys) -> None:
    assert main(tmp_path) == 0
    report = EvalReport.model_validate_json((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert report.gold_pairs == 30
    assert report.hard_negatives == 10
    assert len(report.rows) == 4
    assert all(row.p_at_5 is not None and row.mrr_at_10 is not None for row in report.rows)
    assert "闭集" in (report.notes or "")
    assert len(report.case_study_ids) == 3
    out = capsys.readouterr().out
    assert "P@5=" in out
