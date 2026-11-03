import { useEffect, useState } from "react";
import { evalReport, type EvalReport } from "../lib/api";
import { evalSnapshot } from "../lib/evalSnapshot";
import { Card } from "./ui/Card";

const percent = new Intl.NumberFormat("zh-CN", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const reportTime = new Intl.DateTimeFormat("zh-CN", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Asia/Shanghai",
});

const columns = ["配置", "结构签名", "领域距离", "重排", "P@5", "MRR@10"];

export function EvalDashboard({ report }: { report: EvalReport }) {
  const generatedAt = new Date(report.generated_at);
  return (
    <div className="space-y-5">
      {report.rows?.length ? (
        <>
          <dl className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
            <div className="rounded-lg bg-emerald-50 px-4 py-3">
              <dt className="text-sm">金标准正例</dt>
              <dd className="text-2xl font-bold tabular-nums">{report.gold_pairs}</dd>
            </div>
            <div className="rounded-lg bg-emerald-50 px-4 py-3">
              <dt className="text-sm">困难负例</dt>
              <dd className="text-2xl font-bold tabular-nums">{report.hard_negatives}</dd>
            </div>
            {report.kappa != null && (
              <div className="rounded-lg bg-emerald-50 px-4 py-3">
                <dt className="text-sm">标注一致性 κ</dt>
                <dd className="text-2xl font-bold tabular-nums">{report.kappa.toFixed(3)}</dd>
              </div>
            )}
          </dl>
          <Card className="overflow-hidden">
            <div className="overflow-x-auto focus-visible:outline-2 focus-visible:outline-emerald-700" tabIndex={0} role="region" aria-label="消融实验数据表">
              <table className="w-full min-w-155 text-left">
                <caption className="border-b border-border px-5 py-4 text-left text-lg font-bold">消融实验</caption>
                <thead className="bg-emerald-950 text-sm text-white">
                  <tr>{columns.map((label) => <th key={label} scope="col" className="whitespace-nowrap px-5 py-3">{label}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {report.rows.map((row, index) => (
                    <tr key={`${row.config}-${index}`} className="even:bg-emerald-50">
                      <th scope="row" className="px-5 py-3 font-semibold">{row.config}</th>
                      <td className="px-5 py-3">{row.use_structural ? "开启" : "关闭"}</td>
                      <td className="px-5 py-3">{row.use_domain_distance ? "开启" : "关闭"}</td>
                      <td className="px-5 py-3">{row.use_rerank ? "开启" : "关闭"}</td>
                      <td className="px-5 py-3 font-semibold tabular-nums">{row.p_at_5 == null ? "未出值" : percent.format(row.p_at_5)}</td>
                      <td className="px-5 py-3 font-semibold tabular-nums">{row.mrr_at_10 == null ? "未出值" : row.mrr_at_10.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <p className="text-sm">生成时间 <time dateTime={report.generated_at}>{Number.isNaN(generatedAt.valueOf()) ? report.generated_at : reportTime.format(generatedAt)}</time></p>
        </>
      ) : <Card className="p-5">还没有可展示的评测结果。</Card>}
      {(report.notes || !!report.case_study_ids?.length) && (
        <Card className="space-y-2 p-5">
          <h3 className="font-bold">如何解读结果</h3>
          {report.notes && <p className="leading-relaxed">{report.notes}</p>}
          {!!report.case_study_ids?.length && <p className="text-sm">案例编号 · {report.case_study_ids.join("、")}</p>}
        </Card>
      )}
    </div>
  );
}

function LiveEval() {
  const [report, setReport] = useState<EvalReport>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const request = new AbortController();
    void evalReport("", request.signal).then(
      (value) => { if (!request.signal.aborted) setReport(value); },
      () => { if (!request.signal.aborted) setError("暂时无法加载评测报告。"); },
    );
    return () => request.abort();
  }, [attempt]);

  if (report) return <EvalDashboard report={report} />;
  if (!error) return <p role="status">正在加载评测报告…</p>;
  return (
    <Card className="flex flex-wrap items-center gap-3 p-5">
      <p role="alert">{error}</p>
      <button type="button" className="rounded-lg border border-border px-3 py-1.5 font-semibold hover:bg-emerald-50" onClick={() => {
        setError("");
        setAttempt((value) => value + 1);
      }}>重新加载</button>
    </Card>
  );
}

export function EvalPage({ offline = false }: { offline?: boolean }) {
  return (
    <section className="space-y-5" aria-labelledby="eval-title">
      <header>
        <p className="text-sm font-semibold text-emerald-800">结构匹配评测{offline && " · 离线快照"}</p>
        <h2 id="eval-title" className="mt-2 text-3xl font-bold sm:text-4xl">评测看板</h2>
      </header>
      {offline ? <EvalDashboard report={evalSnapshot} /> : <LiveEval />}
    </section>
  );
}
