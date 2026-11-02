"""评测入口：uv run task eval  →  eval/reports/latest.json + latest.md

TODO(P2-T5)：把这里换成真实实现。当前只是脚手架，保证 API 的 /eval/report 有东西可返回。
不要在这里写假数字——空着比编造好，答辩被问"这 0.71 怎么来的"会当场崩。
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD = REPO_ROOT / "eval" / "gold" / "analogy_pairs.jsonl"
REPORTS = REPO_ROOT / "eval" / "reports"

ABLATIONS = [
    ("A 纯语义(baseline)", False, False, False),
    ("B +结构签名", True, False, False),
    ("C +领域距离", True, True, False),
    ("D 完整", True, True, True),
]


def load_gold() -> list[dict]:
    if not GOLD.exists():
        return []
    rows = []
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> int:
    gold = load_gold()
    positives = [g for g in gold if g.get("id", "").startswith("g")]
    negatives = [g for g in gold if g.get("id", "").startswith("n")]

    report = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gold_pairs": len(positives),
        "hard_negatives": len(negatives),
        "kappa": None,
        "rows": [
            {
                "config": name,
                "use_structural": s,
                "use_domain_distance": d,
                "use_rerank": r,
                "p_at_5": None,
                "mrr_at_10": None,
            }
            for name, s, d, r in ABLATIONS
        ],
        "case_study_ids": [g["id"] for g in positives[:3]],
        "notes": "脚手架：指标待 P2-T5 用真实匹配结果填充",
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    dist = Counter(g.get("group", "?") for g in positives)
    md = [
        "# 评测报告（脚手架）",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 正例：{len(positives)} ｜ 负例：{len(negatives)} ｜ 分组分布：{dict(dist)}",
        "- 指标：待填（P2-T5）",
        "",
        "| 配置 | struct | domain | rerank | P@5 | MRR@10 |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["rows"]:
        md.append(
            f"| {r['config']} | {r['use_structural']} | {r['use_domain_distance']} "
            f"| {r['use_rerank']} | - | - |"
        )
    (REPORTS / "latest.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"gold={len(positives)}P/{len(negatives)}N -> eval/reports/latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
