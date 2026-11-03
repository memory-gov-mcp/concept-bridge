import { setupServer } from "msw/node";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { EvalDashboard } from "../src/components/EvalPage";
import { evalReport } from "../src/lib/api";
import { evalSnapshot } from "../src/lib/evalSnapshot";
import { handlers } from "../src/mocks/handlers";

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());

describe("P4-T7 evaluation", () => {
  it("serves the committed report in mock mode", async () => {
    expect(await evalReport("http://localhost")).toEqual(evalSnapshot);
  });

  it("shows the ablation rows, metrics and the report's interpretation", () => {
    const report = {
      ...evalSnapshot,
      rows: [{ config: "A 纯语义(baseline)", p_at_5: 0.766667, mrr_at_10: 0.961111 }],
      notes: "评测语料为机制闭集。",
    };
    const markup = renderToStaticMarkup(<EvalDashboard report={report} />);
    expect(markup).toContain("A 纯语义(baseline)");
    expect(markup).toContain("76.67%");
    expect(markup).toContain("0.9611");
    expect(markup).toContain("机制闭集");
  });

  it("distinguishes a missing metric or report from a zero score", () => {
    const partial = { ...evalSnapshot, rows: [{ config: "未跑完", p_at_5: null, mrr_at_10: 0 }] };
    const markup = renderToStaticMarkup(<EvalDashboard report={partial} />);
    expect(markup).toContain("未出值");
    expect(markup).toContain("0.0000");
    expect(renderToStaticMarkup(<EvalDashboard report={{ ...evalSnapshot, rows: [] }} />))
      .toContain("还没有可展示的评测结果");
  });
});
