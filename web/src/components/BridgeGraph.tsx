import cytoscape, { type Core, type StylesheetJson } from "cytoscape";
import { useLayoutEffect, useMemo, useRef } from "react";
import type { Bridge, BridgeResult } from "../lib/api";
import { bridgeGraph } from "../lib/bridgeGraph";
import { domainLabel } from "../lib/domain";
import { Card } from "./ui/Card";

const graphStyle: StylesheetJson = [
  {
    selector: "node",
    style: {
      "background-color": "#227763",
      "width": 26,
      "height": 26,
      "border-width": 2,
      "border-color": "#ffffff",
      "label": "data(label)",
      "color": "#1b3029",
      "font-size": 13,
      "font-weight": 600,
      "min-zoomed-font-size": 7,
      "text-wrap": "wrap",
      "text-max-width": "100px",
      "text-valign": "bottom",
      "text-margin-y": 5,
      "text-outline-width": 2,
      "text-outline-color": "#fafbf8",
    },
  },
  { selector: 'node[kind = "structure"]', style: { shape: "round-rectangle" } },
  { selector: 'node[kind = "signal"]', style: { shape: "diamond" } },
  { selector: 'node[kind = "state"]', style: { shape: "hexagon" } },
  { selector: "node.target", style: { "background-color": "#7454ab" } },
  {
    selector: "edge",
    style: {
      "curve-style": "bezier",
      "width": 1.6,
      "line-color": "#75a89b",
      "target-arrow-color": "#75a89b",
      "target-arrow-shape": "triangle",
      "label": "data(label)",
      "font-size": 11,
      "color": "#3b6157",
      "text-outline-color": "#fafbf8",
      "text-outline-width": 2,
      "min-zoomed-font-size": 8,
    },
  },
  {
    selector: "edge.target",
    style: { "line-color": "#a28acb", "target-arrow-color": "#a28acb", "color": "#5c3e8e" },
  },
  { selector: "node.aligned", style: { "border-color": "#f6c750", "border-width": 4 } },
  { selector: "node:grabbed", style: { "border-color": "#164e43", "border-width": 4 } },
];

const buttonClass = "rounded-md border border-border bg-card px-3 py-2 text-xs font-semibold hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-emerald-700 disabled:opacity-50";

function fitGraph(cy: Core) {
  cy.fit(undefined, 28);
  if (cy.zoom() > 1.35) cy.zoom(1.35);
  cy.center();
}

export function BridgeGraph({ result, bridge }: { result: BridgeResult; bridge: Bridge }) {
  const model = useMemo(() => bridgeGraph(result, bridge), [result, bridge]);
  const canvas = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useLayoutEffect(() => {
    if (!canvas.current) return;
    const cy = cytoscape({
      container: canvas.current,
      elements: model.elements,
      style: graphStyle,
      layout: { name: "preset", fit: false },
      minZoom: 0.1,
      maxZoom: 3.5,
      autounselectify: true,
      pixelRatio: 1,
    });
    cyRef.current = cy;

    fitGraph(cy);
    const observer = new ResizeObserver(() => {
      cy.resize();
      fitGraph(cy);
    });
    observer.observe(canvas.current);

    return () => {
      observer.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, [model]);

  function zoom(factor: number) {
    const cy = cyRef.current;
    if (cy) cy.zoom({ level: cy.zoom() * factor, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  }

  return (
    <Card className="space-y-4 overflow-hidden p-4 sm:p-6" aria-label="双域机制图谱">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">双域机制图谱</h2>
          <p className="mt-1 text-sm text-emerald-950/75">{model.nodeCount} 个概念 · 拖动节点，滚动或双指缩放</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={buttonClass} onClick={() => zoom(1 / 1.25)} aria-label="图谱缩小">−</button>
          <button type="button" className={buttonClass} onClick={() => zoom(1.25)} aria-label="图谱放大">+</button>
          <button type="button" className={buttonClass} onClick={() => { if (cyRef.current) fitGraph(cyRef.current); }}>重置视图</button>
        </div>
      </div>
      <figure className="overflow-hidden rounded-xl border border-border bg-background">
        <div className="grid grid-cols-2 gap-2 border-b border-border px-3 py-2 text-xs font-bold sm:px-4 sm:text-sm">
          <p className="text-emerald-800">● 源领域 · {domainLabel(result.source.domain)}</p>
          <p className="text-right text-violet-800">● 目标领域 · {domainLabel(bridge.target_domain)}</p>
        </div>
        <div className="relative h-72 bg-[radial-gradient(#cdd9d1_1px,transparent_1px)] bg-[size:18px_18px] sm:h-[21rem]">
          <div ref={canvas} data-testid="bridge-graph-canvas" aria-hidden="true" className="h-full w-full" />
        </div>
      </figure>
      {model.alignments.length > 0 && (
        <ul aria-label="结构对齐" className="grid gap-2 sm:grid-cols-2">
          {model.alignments.map((row, index) => (
            <li key={index} className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-950">
              <strong>{row.sourceLabel} ↔ {row.targetLabel}</strong>
              <p>{row.reason}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
