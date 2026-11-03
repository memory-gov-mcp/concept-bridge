import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { BridgeResults } from "../src/components/BridgeResults";
import { sample } from "../src/mocks/sample";

describe("P4-T4 result panel", () => {
  it("applies word wrapping throughout the result panel", () => {
    const html = renderToStaticMarkup(<BridgeResults result={sample} />);
    expect(html).toMatch(/<section id="bridge-results" class="[^"]*\bwrap-anywhere\b/);
  });

  it("only offers graph navigation when the result page has a graph", () => {
    const withoutGraph = renderToStaticMarkup(<BridgeResults result={sample} />);
    const withGraph = renderToStaticMarkup(<BridgeResults result={sample} onInspectBridge={() => undefined} />);
    expect(withoutGraph).not.toContain("在图谱中查看第 1 条桥");
    expect(withGraph).toContain('aria-label="在图谱中查看第 1 条桥"');
    expect(withGraph).toContain('aria-label="在图谱中查看第 2 条桥"');
  });

  it("renders a labeled score meter and a button that controls the original excerpt", () => {
    const html = renderToStaticMarkup(<BridgeResults result={sample} />);
    expect(html).toMatch(/<meter[^>]*aria-label="综合"/);
    const control = html.match(/<button[^>]*aria-controls="([^"]+)"[^>]*aria-pressed="false"/);
    expect(control).not.toBeNull();
    expect(html).toContain(`id="${control?.[1]}"`);
    expect(html).toContain(sample.bridges[0].citations[0].span);
  });

  it("links a canonical OpenAlex ID only when the result is backed by a real corpus", () => {
    const paper = sample.bridges[0].citations[0].paper_id;
    const render = (graph_version: string) => renderToStaticMarkup(
      <BridgeResults result={{ ...sample, meta: { ...sample.meta, graph_version, stub: false } }} />,
    );

    expect(render("g-20261103-1")).toContain(`href="https://openalex.org/${paper}"`);
    const fixture = render("fixtures");
    expect(fixture).toContain("引用片段来自演示数据");
    expect(fixture).not.toContain("https://openalex.org/");
  });
});
