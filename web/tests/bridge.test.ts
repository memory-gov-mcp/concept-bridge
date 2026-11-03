import { setupServer } from "msw/node";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { bridge, health, queryError } from "../src/lib/api";
import { handlers } from "../src/mocks/handlers";
import { sample, sampleQuery } from "../src/mocks/sample";

const base = "http://localhost";
const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
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
});
