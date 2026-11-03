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

async function request<T>(path: string, base: string, init?: RequestInit): Promise<T> {
  const timeout = AbortSignal.timeout(15_000);
  const signal = init?.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  let response: Response;
  try {
    response = await fetch(`${base}/api/v1${path}`, { ...init, signal });
  } catch {
    throw new Error(timeout.aborted ? errorMessages.UPSTREAM_TIMEOUT : "无法连接查询服务，请重试。");
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const code = body?.code ?? (response.status === 422 ? "BAD_REQUEST" : "INTERNAL");
    const message = Object.hasOwn(errorMessages, code) ? errorMessages[code] : errorMessages.INTERNAL;
    throw new Error(message);
  }
  if (!body) throw new Error("查询服务返回了无法读取的数据，请重试。");
  return body as T;
}

export function bridge(body: BridgeRequest, base = "", signal?: AbortSignal) {
  return request<BridgeResult>("/bridge", base, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

export function health(base = "") {
  return request<HealthResponse>("/health", base);
}
