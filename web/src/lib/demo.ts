import fixture from "../../../fixtures/bridge.sample.json";
import type { BridgeResult } from "./api";
import catalyst from "../mocks/demo-catalyst.json";
import proteinFolding from "../mocks/demo-protein-folding.json";
import { queryPresets } from "./presets";

const [primary, second, third] = queryPresets;

// JSON 导入的推断类型是宽泛的 string，直接 equals BridgeResult 会报类型不匹配；
// 这里统一在边界处收窄一次，其余地方保持强类型。
const asResult = (value: unknown) => value as BridgeResult;

// 每个预置题都必须有离线快照，否则演示走到那一屏会变成"暂无快照"的死卡片。
// 后两份是用真实 500 条机制语料导出的 BridgeResult（`POST /api/v1/bridge` 原样落盘）。
const replayByQuery: Record<string, BridgeResult> = {
  [primary.query]: asResult(fixture),
  [second.query]: asResult(catalyst),
  [third.query]: asResult(proteinFolding),
};

export const demoSteps = [
  { kind: "question", title: "提出源领域难题", ...primary },
  { kind: "graph", title: "观察双域结构对齐", ...primary },
  { kind: "evidence", title: "核对假设与原文证据", ...primary },
  { kind: "evidence", title: "第二个研究难题", ...second },
  { kind: "evidence", title: "第三个研究难题", ...third },
  { kind: "eval", title: "查看评测结论" },
] as const;

export function getDemoReplay(query: string): BridgeResult | undefined {
  return replayByQuery[query];
}

export function demoDirection(key: string, ownsArrowKeys = false) {
  if (ownsArrowKeys) return;
  if (key === "ArrowRight") return 1;
  if (key === "ArrowLeft") return -1;
}

export function advanceDemo(index: number, direction: -1 | 1) {
  return Math.max(0, Math.min(demoSteps.length - 1, index + direction));
}
