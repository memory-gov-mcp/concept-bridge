// Fields consumed by the UI and mock from contracts/openapi.yaml.
export interface BridgeRequest {
  query: string;
  top_k?: number;
  source_domain?: string | null;
  exclude_domains?: string[];
  debug?: boolean;
}

export interface ConceptRef {
  concept_id: string;
  surface: string;
  type: string;
}

export interface Citation {
  paper_id: string;
  span: string;
  char_start: number;
  char_end: number;
}

export interface Mechanism {
  id: string;
  paper_id: string;
  domain: string;
  subject: ConceptRef;
  action: { verb: string; action_class: string };
  object: ConceptRef;
  conditions?: string[];
  result: string;
  evidence: Omit<Citation, "paper_id"> & { section?: string };
}

export interface GraphNode { id: string; label: string; domain: string; type: string }
export interface GraphEdge { id: string; source: string; target: string; action_class: string }

export interface Alignment {
  source_role: string;
  source_concept_id: string;
  target_role: string;
  target_concept_id: string;
  reason: string;
}

export interface Bridge {
  target_mechanism: Mechanism;
  target_domain: string;
  scores: Record<"structural" | "semantic" | "domain_distance" | "triviality" | "final", number>;
  alignment?: Alignment[];
  transferable_hypothesis: string;
  differences?: string[];
  citations: Citation[];
}

export interface BridgeResult {
  query: string;
  source: {
    domain: string;
    mechanisms?: Mechanism[];
    subgraph?: { nodes?: GraphNode[]; edges?: GraphEdge[] };
  };
  bridges?: Bridge[];
  meta: { latency_ms: number; candidates: number; graph_version: string; degraded?: boolean; stub?: boolean };
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  graph_version: string;
  graph_ready: boolean;
  demo_mode: boolean;
}

export interface EvalRow {
  config: string;
  use_structural?: boolean;
  use_domain_distance?: boolean;
  use_rerank?: boolean;
  p_at_5?: number | null;
  mrr_at_10?: number | null;
}

export interface EvalReport {
  generated_at: string;
  gold_pairs: number;
  hard_negatives: number;
  kappa?: number | null;
  rows?: EvalRow[];
  case_study_ids?: string[];
  notes?: string | null;
}

const errorMessages: Record<string, string> = {
  BAD_REQUEST: "请检查查询内容后重试。",
  QUERY_TOO_SHORT: "请输入至少 2 个字符。",
  GRAPH_NOT_READY: "图谱还在准备，请稍后重试。",
  UPSTREAM_TIMEOUT: "查询超时，请重试。",
  LLM_UNAVAILABLE: "解释服务暂不可用，请稍后重试。",
  NOT_FOUND: "没有找到请求的资源。",
  INTERNAL: "服务暂时出错，请稍后重试。",
};

export function queryError(query: string) {
  const length = [...query.trim()].length;
  if (length < 2) return errorMessages.QUERY_TOO_SHORT;
  if (length > 200) return "查询最多 200 个字符。";
  return "";
}

type JsonObject = Record<string, unknown>;

function record(value: unknown): JsonObject | undefined {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as JsonObject : undefined;
}

function strings(value: unknown, ...keys: string[]) {
  const object = record(value);
  return !!object && keys.every((key) => typeof object[key] === "string");
}

function optionalList(value: unknown, valid: (item: unknown) => boolean) {
  return value === undefined || (Array.isArray(value) && value.every(valid));
}

// Check fields the UI reads before handing the response to React and Cytoscape.
function mechanism(value: unknown) {
  const item = record(value);
  return !!item && strings(item, "id", "domain", "result")
    && strings(item.subject, "concept_id", "surface", "type")
    && strings(item.object, "concept_id", "surface", "type")
    && strings(item.action, "verb", "action_class");
}

function bridgeItem(value: unknown) {
  const item = record(value);
  const scores = record(item?.scores);
  return !!item && !!scores && mechanism(item.target_mechanism)
    && strings(item, "target_domain", "transferable_hypothesis")
    && ["structural", "semantic", "domain_distance", "triviality", "final"].every((key) => Number.isFinite(scores[key]))
    && Array.isArray(item.citations) && item.citations.length > 0 && item.citations.every((value: unknown) => {
      const citation = record(value);
      return !!citation && strings(citation, "paper_id", "span")
        && Number.isInteger(citation.char_start) && Number.isInteger(citation.char_end);
    })
    && optionalList(item.differences, (entry) => typeof entry === "string")
    && optionalList(item.alignment, (entry) => strings(entry, "source_concept_id", "target_concept_id", "reason"));
}

function bridgePayload(body: JsonObject) {
  const source = record(body.source);
  const graph = record(source?.subgraph);
  const meta = record(body.meta);
  return typeof body.query === "string" && !!source && typeof source.domain === "string"
    && optionalList(source.mechanisms, mechanism)
    && (source.subgraph === undefined || (!!graph
      && optionalList(graph.nodes, (entry) => strings(entry, "id", "label", "domain", "type"))
      && optionalList(graph.edges, (entry) => strings(entry, "id", "source", "target", "action_class"))))
    && !!meta && typeof meta.graph_version === "string" && Number.isFinite(meta.latency_ms)
    && optionalList(body.bridges, bridgeItem);
}

function evalPayload(body: JsonObject) {
  return typeof body.generated_at === "string" && Number.isInteger(body.gold_pairs) && Number.isInteger(body.hard_negatives)
    && (body.notes == null || typeof body.notes === "string")
    && (body.kappa == null || Number.isFinite(body.kappa))
    && optionalList(body.case_study_ids, (entry) => typeof entry === "string")
    && optionalList(body.rows, (entry) => {
      const row = record(entry);
      return !!row && typeof row.config === "string"
        && (row.p_at_5 == null || Number.isFinite(row.p_at_5))
        && (row.mrr_at_10 == null || Number.isFinite(row.mrr_at_10));
    });
}

async function request<T>(path: string, base: string, valid: (body: JsonObject) => boolean, init?: RequestInit): Promise<T> {
  const timeout = AbortSignal.timeout(15_000);
  const signal = init?.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  let response: Response;
  try {
    response = await fetch(`${base}/api/v1${path}`, { ...init, signal });
  } catch {
    throw new Error(timeout.aborted ? errorMessages.UPSTREAM_TIMEOUT : "无法连接查询服务，请重试。");
  }

  const body = record(await response.json().catch(() => null));
  if (timeout.aborted) throw new Error(errorMessages.UPSTREAM_TIMEOUT);
  if (!response.ok) {
    const statusCode = response.status === 504 ? "UPSTREAM_TIMEOUT" : response.status === 422 ? "BAD_REQUEST" : "INTERNAL";
    const code = body?.code;
    const message = typeof code === "string" && Object.hasOwn(errorMessages, code) ? errorMessages[code] : errorMessages[statusCode];
    throw new Error(message);
  }
  if (!body || !valid(body)) throw new Error("查询服务返回了无法读取的数据，请重试。");
  return body as T;
}

export function bridge(body: BridgeRequest, base = "", signal?: AbortSignal) {
  return request<BridgeResult>("/bridge", base, bridgePayload, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

export function health(base = "") {
  return request<HealthResponse>("/health", base, (body) => (body.status === "ok" || body.status === "degraded")
    && strings(body, "version", "graph_version") && typeof body.graph_ready === "boolean" && typeof body.demo_mode === "boolean");
}

export function evalReport(base = "", signal?: AbortSignal) {
  return request<EvalReport>("/eval/report", base, evalPayload, { signal });
}
