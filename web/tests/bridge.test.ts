import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { bridge, evalReport, health, queryError } from "../src/lib/api";
import { handlers } from "../src/mocks/handlers";
import { sample, sampleQuery } from "../src/mocks/sample";

const base = "http://localhost";
const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("P4-T1 API", () => {
  it("returns the existing example and reports mock health", async () => {
    expect(await health(base)).toMatchObject({ demo_mode: true });
    const result = await bridge({ query: sampleQuery }, base);
    expect(result).toEqual(sample);
    expect(result.bridges).toHaveLength(2);
  });

  it("honors the result limit and domain exclusion", async () => {
    expect((await bridge({ query: sampleQuery, top_k: 1 }, base)).bridges).toHaveLength(1);
    expect((await bridge({ query: sampleQuery, exclude_domains: ["biology"] }, base)).bridges).toEqual([]);
  });

  it("keeps unsupported queries separate from the fixture", async () => {
    const result = await bridge({ query: "催化剂失活" }, base);
    expect(result).toMatchObject({ query: "催化剂失活", bridges: [], source: { domain: "unknown" } });
  });

  it("reports invalid query lengths and maps the validation response", async () => {
    expect(queryError(" 锂 ")).toBe("请输入至少 2 个字符。");
    expect(queryError("桥".repeat(201))).toBe("查询最多 200 个字符。");
    await expect(bridge({ query: "锂" }, base)).rejects.toThrow("请检查查询内容后重试。");
  });

  it("rejects invalid optional fields and unknown mock request keys", async () => {
    for (const fields of [{ debug: [] }, { source_domain: [] }, { extra: true }]) {
      const response = await fetch(`${base}/api/v1/bridge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: sampleQuery, ...fields }),
      });
      expect(response.status).toBe(422);
    }
  });

  it("shows a friendly error when a successful API response cannot be displayed", async () => {
    server.use(
      http.post("*/api/v1/bridge", () => HttpResponse.json({ ...sample, bridges: [{ ...sample.bridges[0], citations: null }] })),
      http.get("*/api/v1/health", () => HttpResponse.json({ status: "ok" })),
      http.get("*/api/v1/eval/report", () => HttpResponse.json({ rows: [null] })),
    );
    await expect(bridge({ query: sampleQuery }, base)).rejects.toThrow("查询服务返回了无法读取的数据");
    await expect(health(base)).rejects.toThrow("查询服务返回了无法读取的数据");
    await expect(evalReport(base)).rejects.toThrow("查询服务返回了无法读取的数据");
  });

  it("maps a proxy timeout without a JSON error code", async () => {
    server.use(http.post("*/api/v1/bridge", () => new HttpResponse("Gateway timeout", { status: 504 })));
    await expect(bridge({ query: sampleQuery }, base)).rejects.toThrow("查询超时，请重试。");
  });
});
