import fixture from "../../../fixtures/bridge.sample.json";
import type { BridgeResult } from "./api";
import { queryPresets } from "./presets";

const [primary, second, third] = queryPresets;

export const demoSteps = [
  { kind: "question", title: "提出源领域难题", ...primary },
  { kind: "graph", title: "观察双域结构对齐", ...primary },
  { kind: "evidence", title: "核对假设与原文证据", ...primary },
  { kind: "evidence", title: "第二个研究难题", ...second },
  { kind: "evidence", title: "第三个研究难题", ...third },
  { kind: "eval", title: "查看评测结论" },
] as const;

export function getDemoReplay(query: string): BridgeResult | undefined {
  return query === fixture.query ? fixture : undefined;
}

export function demoDirection(key: string) {
  if (key === "ArrowRight") return 1;
  if (key === "ArrowLeft") return -1;
}

export function advanceDemo(index: number, direction: -1 | 1) {
  return Math.max(0, Math.min(demoSteps.length - 1, index + direction));
}
