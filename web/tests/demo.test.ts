import { describe, expect, it } from "vitest";
import { advanceDemo, demoDirection, demoSteps, getDemoReplay } from "../src/lib/demo";

describe("P4-T6 demo", () => {
  it("advances one screen per arrow and stops at the ends", () => {
    expect(demoDirection("ArrowRight")).toBe(1);
    expect(demoDirection("ArrowLeft")).toBe(-1);
    expect(demoDirection("Escape")).toBeUndefined();
    expect(advanceDemo(0, -1)).toBe(0);
    expect(advanceDemo(0, 1)).toBe(1);
    expect(advanceDemo(2, -1)).toBe(1);
    expect(advanceDemo(demoSteps.length - 1, 1)).toBe(demoSteps.length - 1);
  });

  it("lets a focused horizontal region keep both arrow keys", () => {
    expect(demoDirection("ArrowRight", true)).toBeUndefined();
    expect(demoDirection("ArrowLeft", true)).toBeUndefined();
  });

  it("offers the three preset topics and preserves the snapshot's identity", () => {
    expect(demoSteps.filter((step) => "query" in step).map((step) => step.query))
      .toEqual(["锂枝晶抑制", "锂枝晶抑制", "锂枝晶抑制", "催化剂失活", "蛋白质折叠"]);
    const result = getDemoReplay("锂枝晶抑制");
    expect(result?.query).toBe("锂枝晶抑制");
    expect(result?.bridges).toHaveLength(2);
  });

  it("has an offline snapshot for every preset topic", () => {
    // 回归护栏：曾经只有第一个预置题有快照，演示走到第二、三屏会变成"暂无离线快照"的死卡片。
    // 要求 demoSteps 里出现的每个 query 都能 replay 到非空结果。
    const queries = [...new Set(demoSteps.filter((step) => "query" in step).map((step) => step.query))];
    for (const query of queries) {
      const replay = getDemoReplay(query);
      expect(replay, `${query} 缺少离线快照`).toBeDefined();
      expect(replay?.query).toBe(query);
      expect(replay?.bridges?.length ?? 0).toBeGreaterThan(0);
    }
    expect(queries).toEqual(["锂枝晶抑制", "催化剂失活", "蛋白质折叠"]);
  });
});
