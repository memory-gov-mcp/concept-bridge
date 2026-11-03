import type { EvalReport } from "./api";

const snapshots = import.meta.glob<EvalReport>("../../../eval/reports/latest.json", {
  eager: true,
  import: "default",
});

export const evalSnapshot: EvalReport = snapshots["../../../eval/reports/latest.json"] ?? {
  generated_at: "1970-01-01T00:00:00Z",
  gold_pairs: 0,
  hard_negatives: 0,
  rows: [],
  notes: "评测尚未生成，运行 uv run task eval 后刷新",
};
