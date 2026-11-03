import type { ElementDefinition, Position } from "cytoscape";
import { actionLabel } from "./action";
import type { Bridge, BridgeResult, GraphEdge, GraphNode, Mechanism } from "./api";

type Side = "source" | "target";
const nodeId = (side: Side, id: string) => `${side}:${id}`;
const edgeKey = ({ source, target, action_class }: GraphEdge) =>
  JSON.stringify([source, target, action_class]);

function addMechanism(
  nodes: Map<string, GraphNode>,
  edges: Map<string, GraphEdge>,
  mechanism: Mechanism,
) {
  for (const concept of [mechanism.subject, mechanism.object]) {
    if (!nodes.has(concept.concept_id)) {
      nodes.set(concept.concept_id, {
        id: concept.concept_id, label: concept.surface, type: concept.type, domain: mechanism.domain,
      });
    }
  }
  const edge = {
    id: mechanism.id,
    source: mechanism.subject.concept_id,
    target: mechanism.object.concept_id,
    action_class: mechanism.action.action_class,
  };
  if (!edges.has(edgeKey(edge))) edges.set(edgeKey(edge), edge);
}

function clusterElements(
  side: Side,
  nodes: Map<string, GraphNode>,
  edges: Map<string, GraphEdge>,
  emphasized: string[],
): ElementDefinition[] {
  // Put aligned concepts in the columns facing the gap.
  const ordered = [...new Set([...emphasized, ...nodes.keys()])].filter((id) => nodes.has(id));
  const rows = Math.max(1, Math.ceil(Math.sqrt(ordered.length / 2)));
  const direction = side === "source" ? -1 : 1;
  const elements: ElementDefinition[] = ordered.map((id, index) => {
    const node = nodes.get(id)!;
    const col = Math.floor(index / rows);
    const colCount = Math.min(rows, ordered.length - col * rows);
    return {
      group: "nodes",
      data: { id: nodeId(side, id), label: node.label, kind: node.type },
      position: { x: direction * (112 + col * 114), y: (index % rows - (colCount - 1) / 2) * 104 },
      classes: side,
    };
  });
  for (const [key, edge] of edges) {
    if (!nodes.has(edge.source) || !nodes.has(edge.target)) continue;
    elements.push({
      group: "edges",
      data: {
        id: `${side}:edge:${key}`,
        source: nodeId(side, edge.source),
        target: nodeId(side, edge.target),
        label: ordered.length > 30 ? "" : actionLabel(edge.action_class),
      },
      classes: side,
    });
  }
  return elements;
}

export function bridgeGraph(result: BridgeResult, bridge: Bridge) {
  const source = new Map((result.source.subgraph?.nodes ?? []).map((node) => [node.id, node]));
  const sourceEdges = new Map((result.source.subgraph?.edges ?? []).map((edge) => [edgeKey(edge), edge]));
  for (const mechanism of result.source.mechanisms ?? []) addMechanism(source, sourceEdges, mechanism);

  const target = new Map<string, GraphNode>();
  const targetEdges = new Map<string, GraphEdge>();
  addMechanism(target, targetEdges, bridge.target_mechanism);

  const alignments = (bridge.alignment ?? []).map((row) => ({
    source: nodeId("source", row.source_concept_id),
    target: nodeId("target", row.target_concept_id),
    sourceLabel: source.get(row.source_concept_id)?.label ?? row.source_concept_id,
    targetLabel: target.get(row.target_concept_id)?.label ?? row.target_concept_id,
    reason: row.reason,
    visible: source.has(row.source_concept_id) && target.has(row.target_concept_id),
  }));

  return {
    elements: [
      ...clusterElements("source", source, sourceEdges, (bridge.alignment ?? []).map((row) => row.source_concept_id)),
      ...clusterElements("target", target, targetEdges, (bridge.alignment ?? []).map((row) => row.target_concept_id)),
    ],
    alignments,
    nodeCount: source.size + target.size,
  };
}

export function bridgeArc(start: Position, end: Position) {
  const dx = end.x - start.x;
  const arc = Math.min(62, Math.max(22, Math.abs(dx) * 0.18));
  return `M ${start.x} ${start.y} C ${start.x + dx / 3} ${start.y - arc}, ${end.x - dx / 3} ${end.y - arc}, ${end.x} ${end.y}`;
}
