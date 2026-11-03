import { lazy, Suspense, type ComponentProps } from "react";

const Graph = lazy(async () => ({ default: (await import("./BridgeGraph")).BridgeGraph }));

export function LazyBridgeGraph(props: ComponentProps<typeof Graph>) {
  return (
    <Suspense fallback={<p role="status" className="rounded-lg border border-border bg-card p-4">正在加载双域图谱…</p>}>
      <Graph {...props} />
    </Suspense>
  );
}
