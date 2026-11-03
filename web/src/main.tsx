import { useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import { LazyBridgeGraph } from "./components/LazyBridgeGraph";
import { BridgeResults } from "./components/BridgeResults";
import { bridge, health, queryError, type BridgeResult } from "./lib/api";
import "./style.css";

const mock = import.meta.env.DEV && import.meta.env.MODE === "mock";
const initialQuery = "锂枝晶抑制";

function App() {
  const [query, setQuery] = useState(initialQuery);
  const [result, setResult] = useState<BridgeResult>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [service, setService] = useState("连接中");

  async function search(value: string) {
    setError("");
    setLoading(true);
    setResult(undefined);
    try {
      setResult(await bridge({ query: value.trim() }));
    } catch (error) {
      setError(error instanceof Error ? error.message : "查询失败，请重试。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void health().then(
      (status) => setService(status.demo_mode ? "演示 API" : "API 已连接"),
      () => setService("API 暂不可达"),
    );
    void search(initialQuery);
  }, []);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    const invalid = queryError(query);
    if (invalid) setError(invalid);
    else void search(query);
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8 sm:py-12">
        <header className="mb-8 flex items-center justify-between gap-3">
          <p className="text-sm font-bold tracking-widest text-emerald-900">CONCEPTBRIDGE</p>
          <span className="rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold">{mock ? "离线样例 · MSW" : service}</span>
        </header>
        <p className="text-sm font-semibold text-emerald-800">跨学科知识发现</p>
        <h1 className="mt-2 text-5xl font-black tracking-tight sm:text-6xl">概念桥</h1>
        <p className="mt-3 max-w-xl leading-relaxed">输入一个具体的研究难题，查看其他学科中结构相似的机制、可迁移假设与引用。</p>
        <form onSubmit={submit} className="mt-6 max-w-2xl">
          <label htmlFor="query" className="text-sm font-semibold">研究难题</label>
          <div className="mt-2 flex gap-2">
            <input id="query" value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 rounded-lg border border-emerald-900/25 bg-card px-4 py-3 focus-visible:outline-2 focus-visible:outline-emerald-700" />
            <button disabled={loading} className="rounded-lg bg-emerald-900 px-4 py-3 text-sm font-bold text-white hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-65">查找跨域桥</button>
          </div>
        </form>
        {loading && <p role="status" className="mt-5 text-sm">正在查找结构相似的机制…</p>}
        {error && <p role="alert" className="mt-5 rounded-lg bg-red-100 p-3 text-sm text-red-900">{error}</p>}
        {result?.bridges?.[0] && (
          <div className="mt-6"><LazyBridgeGraph result={result} bridge={result.bridges[0]} /></div>
        )}
        {result && <BridgeResults result={result} />}
      </div>
    </main>
  );
}

const root = createRoot(document.getElementById("root")!);

async function start() {
  if (mock) {
    const { worker } = await import("./mocks/browser");
    await worker.start({
      onUnhandledRequest(request, print) {
        if (new URL(request.url).pathname.startsWith("/api/v1/")) print.error();
      },
    });
  }
  root.render(<App />);
}

void start().catch(() => {
  root.render(<p role="alert" className="p-6">无法启动离线样例。请允许本站使用 Service Worker 后刷新。</p>);
});
