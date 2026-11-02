"""把机制列表收成异构图：概念是点，机制是边。"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from ..common.schemas import GraphEdge, GraphNode, MechanismUnit


@dataclass
class BuiltGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    graph: nx.Graph


def build_graph(mechanisms: list[MechanismUnit]) -> BuiltGraph:
    """同一 concept_id 只保留第一次出现的标签与领域。边按机制 id 保留，允许平行边。"""
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    graph: nx.Graph = nx.Graph()

    for mechanism in mechanisms:
        for concept in (mechanism.subject, mechanism.object):
            if concept.concept_id not in nodes:
                nodes[concept.concept_id] = GraphNode(
                    id=concept.concept_id,
                    label=concept.surface,
                    domain=mechanism.domain,
                    type=concept.type,
                )
            graph.add_node(concept.concept_id)
        edges.append(
            GraphEdge(
                id=mechanism.id,
                source=mechanism.subject.concept_id,
                target=mechanism.object.concept_id,
                action_class=mechanism.action.action_class,
            )
        )
        graph.add_edge(mechanism.subject.concept_id, mechanism.object.concept_id)

    return BuiltGraph(nodes=list(nodes.values()), edges=edges, graph=graph)
