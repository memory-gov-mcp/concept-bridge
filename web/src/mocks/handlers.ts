import { http, HttpResponse } from "msw";
import type { BridgeRequest, BridgeResult, HealthResponse } from "../lib/api";
import { evalSnapshot } from "../lib/evalSnapshot";
import { sample, sampleQuery } from "./sample";

function invalid(field: string) {
  return HttpResponse.json(
    { detail: [{ loc: ["body", field], msg: "Invalid value", type: "value_error" }] },
    { status: 422 },
  );
}

export const handlers = [
  http.get("*/api/v1/eval/report", () => HttpResponse.json(evalSnapshot)),
  http.get("*/api/v1/health", () => HttpResponse.json<HealthResponse>({
    status: "ok",
    version: "0.1.0",
    graph_version: sample.meta.graph_version,
    graph_ready: true,
    demo_mode: true,
  })),
  http.post("*/api/v1/bridge", async ({ request }) => {
    const body = await request.json().catch(() => null) as Partial<BridgeRequest> | null;
    if (typeof body?.query !== "string" || [...body.query].length < 2 || [...body.query].length > 200) {
      return invalid("query");
    }
    const { query, top_k = 5, exclude_domains = [] } = body;
    if (!Number.isInteger(top_k) || top_k < 1 || top_k > 20) return invalid("top_k");
    if (!Array.isArray(exclude_domains) || exclude_domains.some((domain) => typeof domain !== "string")) {
      return invalid("exclude_domains");
    }
    if (query !== sampleQuery) {
      return HttpResponse.json<BridgeResult>({
        query, source: { domain: "unknown", mechanisms: [], subgraph: { nodes: [], edges: [] } },
        bridges: [], meta: { ...sample.meta, candidates: 0, latency_ms: 0 },
      });
    }
    const bridges = sample.bridges.filter((item) => !exclude_domains.includes(item.target_domain));
    return HttpResponse.json({ ...sample, bridges: bridges.slice(0, top_k) });
  }),
];
