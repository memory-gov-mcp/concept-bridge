import { describe, expect, it } from "vitest";
import type { BridgeResult } from "../src/lib/api";
import { bridgeGraph } from "../src/lib/bridgeGraph";
import { sample } from "../src/mocks/sample";

describe("双域图模型", () => {
  it("renders each domain in a separate cluster and connects the provided alignment", () => {
    const result: BridgeResult = sample;
    const model = bridgeGraph(result, sample.bridges[0]);
    expect(model.nodeCount).toBe(6);
    expect(model.alignments[0]).toMatchObject({
      source: "source:c_sei_film", target: "target:c_plasma_membrane",
      sourceLabel: "SEI 膜", targetLabel: "细胞膜", visible: true,
    });
    expect(model.elements.filter((item) => item.group === "edges")).toHaveLength(3);
    for (const item of model.elements.filter((item) => item.group === "nodes")) {
      expect(Math.sign(item.position!.x)).toBe(item.classes === "source" ? -1 : 1);
    }
  });

  it("adds source concepts from mechanisms when no subgraph is supplied", () => {
    const model = bridgeGraph({ ...sample, source: { ...sample.source, subgraph: undefined } }, sample.bridges[0]);
    expect(model.nodeCount).toBe(6);
    expect(model.alignments.every((row) => row.visible)).toBe(true);
  });

  it("keeps text for a missing endpoint without drawing an invented arc", () => {
    const bridge = {
      ...sample.bridges[0],
      alignment: [{ ...sample.bridges[0].alignment[0], target_concept_id: "missing" }],
    };
    const model = bridgeGraph(sample, bridge);
    expect(model.alignments[0]).toMatchObject({ targetLabel: "missing", visible: false });
  });

  it("lays out 200 nodes without duplicate IDs or overlapping node positions", () => {
    const nodes = Array.from({ length: 194 }, (_, i) => ({
      id: `extra-${i}`, label: `节点 ${i}`, domain: sample.source.domain, type: "structure",
    }));
    const result = {
      ...sample, source: { ...sample.source, subgraph: {
        ...sample.source.subgraph, nodes: [...sample.source.subgraph.nodes, ...nodes],
      } },
    };
    const model = bridgeGraph(result, sample.bridges[0]);
    expect(model.nodeCount).toBe(200);
    const items = model.elements.filter((item) => item.group === "nodes");
    expect(new Set(items.map((item) => item.data.id)).size).toBe(200);
    expect(new Set(items.map((item) => JSON.stringify(item.position))).size).toBe(200);
  });
});
