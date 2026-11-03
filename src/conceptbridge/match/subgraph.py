"""多步机制子图。超过 8 个概念节点就退回单条机制，避免 VF2 和编辑距离卡住。

近似距离只比较节点类型与边动作的排序差，不跑精确 GED。
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
from networkx.algorithms.isomorphism import DiGraphMatcher

from ..common.schemas import MechanismUnit
from .structural import struct_sim

NODE_LIMIT = 8


@dataclass(frozen=True)
class SubgraphMatch:
    mode: str
    degraded: bool
    distance: float
    source_mechanism_id: str
    target_mechanism_id: str


def _node_count(mechanisms: list[MechanismUnit]) -> int:
    ids: set[str] = set()
    for mechanism in mechanisms:
        ids.add(mechanism.subject.concept_id)
        ids.add(mechanism.object.concept_id)
    return len(ids)


def _graph(mechanisms: list[MechanismUnit]) -> nx.DiGraph:
    graph: nx.DiGraph = nx.DiGraph()
    for mechanism in mechanisms:
        graph.add_node(mechanism.subject.concept_id, type=mechanism.subject.type)
        graph.add_node(mechanism.object.concept_id, type=mechanism.object.type)
        graph.add_edge(
            mechanism.subject.concept_id,
            mechanism.object.concept_id,
            action=mechanism.action.action_class,
        )
    return graph


def _triple(source: MechanismUnit, target: MechanismUnit) -> SubgraphMatch:
    distance = 1.0 - struct_sim(source.signature, target.signature)
    return SubgraphMatch(
        mode="triple",
        degraded=True,
        distance=distance,
        source_mechanism_id=source.id,
        target_mechanism_id=target.id,
    )


def _approx_ged(left: nx.DiGraph, right: nx.DiGraph) -> float:
    """类型与动作的排序差。精确 GED 在 8 个节点上仍可能长时间搜索。"""

    def labels(graph: nx.DiGraph, kind: str) -> list[str]:
        if kind == "node":
            return sorted(str(data.get("type", "")) for _, data in graph.nodes(data=True))
        return sorted(str(data.get("action", "")) for _, _, data in graph.edges(data=True))

    delta = 0
    for kind in ("node", "edge"):
        left_labels = labels(left, kind)
        right_labels = labels(right, kind)
        delta += abs(len(left_labels) - len(right_labels))
        delta += sum(item != other for item, other in zip(left_labels, right_labels, strict=False))
    return float(delta)


def match_subgraphs(
    source: list[MechanismUnit],
    target: list[MechanismUnit],
) -> SubgraphMatch:
    """节点数不超过 NODE_LIMIT 时先试 VF2，对不上再给近似距离。"""
    if not source or not target:
        return SubgraphMatch(
            mode="triple",
            degraded=True,
            distance=1.0,
            source_mechanism_id=source[0].id if source else "",
            target_mechanism_id=target[0].id if target else "",
        )
    if _node_count(source) > NODE_LIMIT or _node_count(target) > NODE_LIMIT:
        return _triple(source[0], target[0])
    left = _graph(source)
    right = _graph(target)
    matcher = DiGraphMatcher(
        left,
        right,
        node_match=lambda left_node, right_node: left_node.get("type") == right_node.get("type"),
        edge_match=lambda left_edge, right_edge: left_edge.get("action") == right_edge.get("action"),
    )
    if matcher.is_isomorphic():
        return SubgraphMatch(
            mode="vf2",
            degraded=False,
            distance=0.0,
            source_mechanism_id=source[0].id,
            target_mechanism_id=target[0].id,
        )
    return SubgraphMatch(
        mode="ged",
        degraded=False,
        distance=_approx_ged(left, right),
        source_mechanism_id=source[0].id,
        target_mechanism_id=target[0].id,
    )
