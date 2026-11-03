// Fields consumed by the UI and mock from contracts/openapi.yaml.
export interface BridgeRequest {
  query: string;
  top_k?: number;
  source_domain?: string | null;
  exclude_domains?: string[];
  debug?: boolean;
}

export interface Mechanism {
  id: string;
  subject: { surface: string };
  action: { verb: string };
  object: { surface: string };
  result: string;
}

export interface BridgeResult {
  query: string;
  source: {
    domain: string;
    mechanisms?: Mechanism[];
    subgraph?: {
      nodes?: { id: string; label: string; domain: string; type: string }[];
      edges?: { id: string; source: string; target: string; action_class: string }[];
    };
  };
  bridges?: {
    target_mechanism: Mechanism;
    target_domain: string;
    scores: Record<"structural" | "semantic" | "domain_distance" | "triviality" | "final", number>;
    alignment?: { reason: string }[];
    transferable_hypothesis: string;
    differences?: string[];
    citations: { paper_id: string; span: string; char_start: number; char_end: number }[];
  }[];
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
  const signal = AbortSignal.timeout(15_000);
  let response: Response;
  try {
    response = await fetch(`${base}/api/v1${path}`, { ...init, signal });
  } catch {
    throw new Error(signal.aborted ? errorMessages.UPSTREAM_TIMEOUT : "无法连接查询服务，请重试。");
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

export function bridge(body: BridgeRequest, base = "") {
  return request<BridgeResult>("/bridge", base, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function health(base = "") {
  return request<HealthResponse>("/health", base);
}
