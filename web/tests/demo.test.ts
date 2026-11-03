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

  it("offers the three preset topics and preserves the snapshot's identity", () => {
    expect(demoSteps.filter((step) => "query" in step).map((step) => step.query))
      .toEqual(["锂枝晶抑制", "锂枝晶抑制", "锂枝晶抑制", "催化剂失活", "蛋白质折叠"]);
    const result = getDemoReplay("锂枝晶抑制");
    expect(result?.query).toBe("锂枝晶抑制");
    expect(result?.bridges).toHaveLength(2);
    expect(getDemoReplay("蛋白质折叠")).toBeUndefined();
    expect(getDemoReplay("催化剂失活")).toBeUndefined();
  });
});
