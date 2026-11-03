import { useEffect, useState } from "react";
import { bridge, type BridgeResult } from "../lib/api";
import { advanceDemo, demoDirection, demoSteps, getDemoReplay } from "../lib/demo";
import { LazyBridgeGraph } from "./LazyBridgeGraph";
import { BridgeResults } from "./BridgeResults";
import { Card } from "./ui/Card";

const buttonClass = "rounded-lg border border-border bg-card px-3 py-2 text-sm font-semibold hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-emerald-700 disabled:opacity-50";
type SlideKind = "graph" | "evidence";

function ResultSlide({ result, kind, offline }: { result: BridgeResult; kind: SlideKind; offline: boolean }) {
  const selected = result.bridges?.[0];
  const isSampleCorpus = !offline && (result.meta.stub || result.meta.graph_version === "fixtures");
  return (
    <div className="space-y-4">
      {isSampleCorpus && <p className="rounded-lg bg-amber-100 px-4 py-2 text-sm text-amber-950">当前 API 使用样例语料，结果仅用于演示。</p>}
      {kind === "graph" && selected
        ? <LazyBridgeGraph result={result} bridge={selected} />
        : <BridgeResults result={result} />}
    </div>
  );
}

function LiveSlide({ query, kind }: { query: string; kind: SlideKind }) {
  const [result, setResult] = useState<BridgeResult>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const request = new AbortController();
    void bridge({ query }, "", request.signal).then(
      (value) => { if (!request.signal.aborted) setResult(value); },
      () => { if (!request.signal.aborted) setError("演示查询失败，请重试或切换到离线回放。"); },
    );
    return () => request.abort();
  }, [query, attempt]);

  if (result?.meta.stub && !getDemoReplay(query)) {
    return <Card className="p-5">当前 API 仅返回离线样例，这个预置题目暂时无法实时演示。</Card>;
  }
  if (result) return <ResultSlide result={result} kind={kind} offline={false} />;
  if (!error) return <p role="status">正在查询「{query}」…</p>;
  return (
    <Card className="flex flex-wrap items-center gap-3 p-5">
      <p role="alert">{error}</p>
      <button type="button" className={buttonClass} onClick={() => {
        setError("");
        setAttempt((value) => value + 1);
      }}>重试</button>
    </Card>
  );
}

function DemoScene({ step, offline }: { step: (typeof demoSteps)[number]; offline: boolean }) {
  if (step.kind === "recap") return <Card className="p-6"><p>演示结束。可按左方向键返回任一示例。</p></Card>;
  if (step.kind === "question") {
    return (
      <Card className="space-y-4 p-8 sm:p-12">
        <p className="text-sm font-bold tracking-widest text-emerald-800">预置研究难题</p>
        <p className="text-4xl font-bold sm:text-6xl">{step.query}</p>
        <p className="max-w-xl text-lg leading-relaxed">{step.description}</p>
      </Card>
    );
  }
  if (!offline) return <LiveSlide key={step.query} query={step.query} kind={step.kind} />;
  const replay = getDemoReplay(step.query);
  if (replay) return <ResultSlide result={replay} kind={step.kind} offline />;
  return (
    <Card className="space-y-3 p-6">
      <p className="text-xl font-bold">{step.query}</p>
      <p>{step.description}</p>
      <p className="text-sm text-emerald-950/75">这个题目暂无离线快照。连接后端后，可以切换到实时查询演示。</p>
    </Card>
  );
}

export function DemoPage() {
  const [index, setIndex] = useState(0);
  const [offline, setOffline] = useState(true);
  const step = demoSteps[index];

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.isComposing || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (event.target instanceof HTMLElement && (
        event.target.isContentEditable || event.target.matches("input, textarea, select")
      )) return;
      const direction = demoDirection(event.key);
      if (!direction) return;
      event.preventDefault();
      if (!event.repeat) setIndex((current) => advanceDemo(current, direction));
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => { window.scrollTo(0, 0); }, [index]);

  return (
    <section className="space-y-6" aria-labelledby="demo-title">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-emerald-800">跨域机制演示</p>
          <h1 id="demo-title" className="mt-2 text-3xl font-bold sm:text-4xl">演示模式</h1>
        </div>
        <div className="flex flex-wrap gap-2" aria-label="演示数据来源" role="group">
          <button type="button" className={buttonClass} aria-pressed={offline} onClick={() => setOffline(true)}>离线回放</button>
          <button type="button" className={buttonClass} aria-pressed={!offline} onClick={() => setOffline(false)}>实时查询</button>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-3" aria-label="演示进度" role="group">
        <button type="button" className={buttonClass} disabled={index === 0} onClick={() => setIndex((current) => advanceDemo(current, -1))}>← 上一屏</button>
        <button type="button" className={buttonClass} disabled={index === demoSteps.length - 1} onClick={() => setIndex((current) => advanceDemo(current, 1))}>下一屏 →</button>
        <p role="status" className="text-sm font-semibold">第 {index + 1} / {demoSteps.length} 屏 · {step.title}</p>
        <p className="text-sm text-emerald-950/75 sm:ml-auto">使用 ← → 切换</p>
      </div>

      <DemoScene step={step} offline={offline} />
    </section>
  );
}
