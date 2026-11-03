import { useId, useState } from "react";
import { actionLabel } from "../lib/action";
import type { BridgeResult, Mechanism } from "../lib/api";
import { domainLabel } from "../lib/domain";
import { Card } from "./ui/Card";

type Bridge = NonNullable<BridgeResult["bridges"]>[number];
type Citation = Bridge["citations"][number];

const scoreLabels = [
  ["final", "综合"], ["structural", "结构"], ["semantic", "语义"],
  ["domain_distance", "领域距离"], ["triviality", "琐碎惩罚"],
] as const;

function MechanismText({ mechanism }: { mechanism: Mechanism }) {
  return (
    <div>
      <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1 font-semibold wrap-anywhere">
        <span>{mechanism.subject.surface}</span>
        <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-900">{actionLabel(mechanism.action.action_class)} →</span>
        <span>{mechanism.object.surface}</span>
      </p>
      <p className="mt-1 font-mono text-xs text-emerald-950/75 wrap-anywhere">{mechanism.action.verb}</p>
      <p className="mt-1 text-sm leading-relaxed text-emerald-950/80">{mechanism.result}</p>
    </div>
  );
}

function ScoreMeters({ scores }: { scores: Bridge["scores"] }) {
  return (
    <div>
      <h4 className="text-sm font-bold">评分 · 0 至 1</h4>
      <dl className="mt-2 grid grid-cols-2 gap-2 text-sm">
        {scoreLabels.map(([key, label]) => (
          <div key={key} className="grid grid-cols-[1fr_auto] items-baseline gap-x-2 rounded-lg bg-background px-3 py-2">
            <dt>{label}</dt>
            <dd className="font-bold tabular-nums">{scores[key].toFixed(2)}</dd>
            <dd className="col-span-2">
              <meter className="block h-3 w-full" min={0} max={1} value={scores[key]} aria-label={label} />
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function CitationList({ citations, sample }: { citations: Citation[]; sample: boolean }) {
  const prefix = useId();
  const [highlighted, setHighlighted] = useState<Citation | null>(null);

  return (
    <div>
      <h4 className="text-sm font-bold">引用片段</h4>
      {citations.map((citation, i) => {
        const excerptId = `${prefix}-excerpt-${i}`;
        const active = citation === highlighted;
        const openAlexId = /^(?:https:\/\/openalex\.org\/)?(W[0-9]+)$/.exec(citation.paper_id)?.[1];
        return (
        <figure key={excerptId} className={`mt-2 rounded-lg border p-3 text-sm ${active ? "border-amber-400 bg-amber-50" : "border-border bg-background"}`}>
            <figcaption>
              <button
                type="button"
                className="rounded-md border border-emerald-700/40 px-2 py-1 text-xs font-semibold text-emerald-950 hover:bg-emerald-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 aria-pressed:bg-emerald-100"
                aria-controls={excerptId}
                aria-pressed={active}
                onClick={() => setHighlighted(active ? null : citation)}
              >
                高亮原文 {i + 1}
              </button>
              <p className="mt-2 break-all text-xs leading-relaxed text-emerald-950/75">
                {sample ? "样例来源" : "文献"} {citation.paper_id} · 字符 {citation.char_start}–{citation.char_end}
                {!sample && openAlexId && (
                  <>
                    {" · "}
                    <a
                      className="font-semibold underline underline-offset-2"
                      href={`https://openalex.org/${openAlexId}`}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`OpenAlex 文献记录 ${openAlexId}`}
                    >
                      OpenAlex 文献记录
                    </a>
                  </>
                )}
              </p>
            </figcaption>
            <blockquote id={excerptId} className="mt-2 border-l-2 border-emerald-700 pl-3 leading-relaxed whitespace-pre-wrap wrap-anywhere">
              {active ? <mark className="rounded-sm bg-amber-200 text-emerald-950">{citation.span}</mark> : citation.span}
            </blockquote>
          </figure>
        );
      })}
    </div>
  );
}

export function BridgeResults({ result, onInspectBridge }: {
  result: BridgeResult;
  onInspectBridge?: (index: number) => void;
}) {
  const bridges = result.bridges ?? [];
  const sample = result.meta.stub === true || result.meta.graph_version === "fixtures";
  return (
    <section id="bridge-results" className="mt-8 space-y-5" aria-label="桥接结果">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="min-w-0 text-2xl font-bold wrap-anywhere">{result.query}</h2>
        <p className="text-sm text-emerald-950/75">{bridges.length} 条跨域桥 · {result.meta.latency_ms} 毫秒</p>
      </div>
      {sample && <p className="rounded-lg bg-amber-100 px-4 py-2 text-sm text-amber-950">样例结果 · 引用片段来自演示数据</p>}
      {result.meta.degraded && <p className="rounded-lg bg-amber-100 px-4 py-2 text-sm text-amber-950">服务处于降级模式，结果可能不完整。</p>}
      {!bridges.length && <Card className="p-5">没有找到跨域桥。可以换一个具体的研究难题再试。</Card>}
      {!!result.source.mechanisms?.length && (
        <Card className="space-y-4 p-5">
          <h3 className="text-xs font-bold tracking-widest text-emerald-800">源机制 · {domainLabel(result.source.domain)}</h3>
          {result.source.mechanisms.map((mechanism) => <MechanismText key={mechanism.id} mechanism={mechanism} />)}
        </Card>
      )}
      {bridges.map((item, index) => (
        <Card key={item.target_mechanism.id} className="grid gap-6 p-5 sm:p-7 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="min-w-0 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-xs font-bold tracking-widest text-emerald-800">跨域桥 {String(index + 1).padStart(2, "0")} · {domainLabel(item.target_domain)}</h3>
              {onInspectBridge && (
                <button type="button" className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-emerald-900 hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-emerald-700"
                  aria-controls="bridge-graph" aria-label={`在图谱中查看第 ${index + 1} 条桥`} onClick={() => onInspectBridge(index)}>
                  在图谱中查看 ↑
                </button>
              )}
            </div>
            <MechanismText mechanism={item.target_mechanism} />
            <div className="rounded-lg bg-emerald-50 p-4">
              <h4 className="text-sm font-bold text-emerald-800">可迁移假设</h4>
              <p className="mt-1 leading-relaxed">{item.transferable_hypothesis}</p>
            </div>
            {([["对齐理由", item.alignment?.map((row) => row.reason)], ["关键差异", item.differences]] as const).map(([title, rows]) => rows?.length ? (
              <div key={title} className="rounded-lg border border-border bg-background p-4">
                <h4 className="text-sm font-bold">{title}</h4>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{rows.map((row, i) => <li key={i}>{row}</li>)}</ul>
              </div>
            ) : null)}
          </div>
          <div className="space-y-5 border-border lg:border-l lg:pl-6">
            <ScoreMeters scores={item.scores} />
            <CitationList citations={item.citations} sample={sample} />
          </div>
        </Card>
      ))}
    </section>
  );
}
