import type { BridgeResult, Mechanism } from "../lib/api";
import { Card } from "./ui/Card";

const domains: Record<string, string> = {
  materials_science: "材料科学", biology: "生物学", chemistry: "化学",
  medicine: "医学", physics: "物理学", computer_science: "计算机科学", unknown: "领域待定",
};
const domainLabel = (domain: string) => domains[domain] ?? domain;
const scoreLabels = {
  final: "综合", structural: "结构", semantic: "语义", domain_distance: "领域距离", triviality: "琐碎惩罚",
} as const;

function MechanismText({ mechanism }: { mechanism: Mechanism }) {
  return (
    <div>
      <p className="font-semibold">{mechanism.subject.surface} → {mechanism.action.verb} → {mechanism.object.surface}</p>
      <p className="mt-1 text-sm leading-relaxed text-emerald-950/80">{mechanism.result}</p>
    </div>
  );
}

export function BridgeResults({ result }: { result: BridgeResult }) {
  const bridges = result.bridges ?? [];
  return (
    <div className="mt-8 space-y-5">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="text-2xl font-bold">{result.query}</h2>
        <p className="text-sm text-emerald-950/75">{bridges.length} 条跨域桥 · {result.meta.latency_ms} 毫秒</p>
      </div>
      {result.meta.stub && <p className="rounded-lg bg-amber-100 px-4 py-2 text-sm text-amber-950">样例结果 · 引用片段来自演示数据</p>}
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
          <div className="space-y-4">
            <h3 className="text-xs font-bold tracking-widest text-emerald-800">跨域桥 {String(index + 1).padStart(2, "0")} · {domainLabel(item.target_domain)}</h3>
            <MechanismText mechanism={item.target_mechanism} />
            <div className="rounded-lg bg-emerald-50 p-4">
              <h4 className="text-sm font-bold text-emerald-800">可迁移假设</h4>
              <p className="mt-1 leading-relaxed">{item.transferable_hypothesis}</p>
            </div>
            {([["对齐理由", item.alignment?.map((row) => row.reason)], ["关键差异", item.differences]] as const).map(([title, rows]) => rows?.length ? (
              <div key={title}>
                <h4 className="text-sm font-bold">{title}</h4>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{rows.map((row, i) => <li key={i}>{row}</li>)}</ul>
              </div>
            ) : null)}
          </div>
          <div className="space-y-5 border-border lg:border-l lg:pl-6">
            <dl className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(scoreLabels).map(([key, label]) => (
                <div key={key} className="rounded-lg bg-background px-3 py-2">
                  <dt>{label}</dt>
                  <dd className="font-bold tabular-nums">{item.scores[key as keyof typeof scoreLabels].toFixed(2)}</dd>
                </div>
              ))}
            </dl>
            <div>
              <h4 className="text-sm font-bold">引用片段</h4>
              {item.citations.map((citation, i) => (
                <figure key={i} className="mt-2 border-l-2 border-emerald-700 pl-3 text-sm">
                  <blockquote className="break-words leading-relaxed">{citation.span}</blockquote>
                  <figcaption className="mt-1 font-mono text-xs">{citation.paper_id} · {citation.char_start}–{citation.char_end}</figcaption>
                </figure>
              ))}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
