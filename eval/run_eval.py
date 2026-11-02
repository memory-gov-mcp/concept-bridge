"""评测入口：uv run task eval  →  eval/reports/latest.json + latest.md

指标由 conceptbridge.match.gold_eval 在金标准闭集上算出来。
"""

from __future__ import annotations

from conceptbridge.match.gold_eval import main

if __name__ == "__main__":
    raise SystemExit(main())
