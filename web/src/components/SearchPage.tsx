import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { bridge, health, queryError, type BridgeResult } from "../lib/api";
import { domainLabel } from "../lib/domain";
import { queryPresets } from "../lib/presets";
import { LazyBridgeGraph } from "./LazyBridgeGraph";
import { BridgeResults } from "./BridgeResults";

const initialQuery = queryPresets[0].query;

export function SearchPage({ mock }: { mock: boolean }) {
  const [query, setQuery] = useState<string>(initialQuery);
  const [result, setResult] = useState<BridgeResult>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [service, setService] = useState("连接中");
  const [selectedBridge, setSelectedBridge] = useState(0);
  const active = useRef<AbortController | null>(null);
  const bridges = result?.bridges ?? [];
  const focusedBridge = bridges[selectedBridge];

  const search = useCallback(async (value: string) => {
    active.current?.abort();
    const request = new AbortController();
    active.current = request;
    setQuery(value);
    setError("");
    setLoading(true);
    setResult(undefined);
    setSelectedBridge(0);
    try {
      const response = await bridge({ query: value }, "", request.signal);
      if (!request.signal.aborted) setResult(response);
    } catch (error) {
      if (!request.signal.aborted) setError(error instanceof Error ? error.message : "查询失败，请重试。");
    } finally {
      if (!request.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    if (!mock) {
      void health().then(
        (status) => { if (mounted) setService(status.demo_mode ? "演示 API" : "API 已连接"); },
        () => { if (mounted) setService("API 暂不可达"); },
      );
    }
    void search(initialQuery);
    return () => {
      mounted = false;
      active.current?.abort();
    };
  }, [mock, search]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const invalid = queryError(query);
    if (invalid) setError(invalid);
    else void search(query.trim());
  }

  return (
    <>
      <section aria-labelledby="search-title" className="rounded-2xl border border-border bg-card p-5 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-semibold tracking-wide text-emerald-800">跨学科知识发现</p>
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-900">{mock ? "离线样例 · MSW" : service}</span>
        </div>
        <h1 id="search-title" className="mt-2 text-4xl font-black tracking-tight sm:text-5xl">从其他学科寻找解法</h1>
        <p className="mt-3 max-w-2xl leading-relaxed">输入一个具体的研究难题，查看结构相似的机制、可迁移假设与文献证据。</p>
        <form onSubmit={submit} className="mt-6 max-w-2xl">
          <label htmlFor="query" className="text-sm font-semibold">研究难题</label>
          <div className="mt-2 flex flex-wrap gap-2">
            <input id="query" value={query} onChange={(event) => { setQuery(event.target.value); setError(""); }}
              placeholder="例如，怎样抑制锂枝晶生长？"
              className="min-w-32 flex-1 rounded-lg border border-emerald-900/25 bg-white px-4 py-3 focus-visible:outline-2 focus-visible:outline-emerald-700" />
            <button type="submit" className="rounded-lg bg-emerald-900 px-4 py-3 text-sm font-bold text-white hover:bg-emerald-800">查找跨域桥</button>
          </div>
        </form>
        <fieldset className="mt-5">
          <legend className="text-sm font-semibold">试试示例</legend>
          <div className="mt-2 grid max-w-2xl gap-2 sm:grid-cols-3">
            {queryPresets.map((item) => (
              <button type="button" key={item.query} onClick={() => void search(item.query)}
                className="rounded-lg border border-border bg-background px-3 py-2 text-left hover:border-emerald-700 hover:bg-emerald-50">
                <span className="block text-sm font-semibold">{item.query}</span>
                <span className="block text-xs text-emerald-950/75">{item.description}</span>
              </button>
            ))}
          </div>
          {mock && <p className="mt-2 text-xs text-emerald-950/75">离线样例包含「锂枝晶抑制」结果，其他示例可接入 API 运行。</p>}
        </fieldset>
      </section>
      <div aria-busy={loading}>
        {loading && <p role="status" className="mt-5 rounded-lg border border-border bg-card p-4 text-sm">正在查找结构相似的机制…</p>}
        {error && <p role="alert" className="mt-5 rounded-lg bg-red-100 p-3 text-sm text-red-900">{error}</p>}
        {result && focusedBridge && (
          <section className="mt-6 space-y-3" aria-label="跨域桥图谱">
            {bridges.length > 1 && (
              <label className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                选择图谱中的跨域桥
                <select value={selectedBridge} onChange={(event) => setSelectedBridge(Number(event.target.value))}
                  className="min-w-0 max-w-full rounded-md border border-border bg-card px-3 py-2">
                  {bridges.map((item, index) => (
                    <option key={item.target_mechanism.id} value={index}>
                      {index + 1}. {domainLabel(item.target_domain)} · {item.target_mechanism.subject.surface}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <LazyBridgeGraph result={result} bridge={focusedBridge} />
          </section>
        )}
        {result && <BridgeResults result={result} />}
      </div>
    </>
  );
}
