"""统一的图谱快照来源（RFC-P1-002）。

问题：`/bridge` 走 `match.pipeline` 的快照，而 `/mechanisms/{id}`、`/graph/subgraph`、
`/health` 各自读死 `bridge.sample.json`。结果是 bridge 返回真实语料的机制 ID 时，
点节点会 404，health 的 graph_version 也和实际图谱不一致。

本模块只做一件事：**让四个端点读同一份快照、报同一个版本**。

依赖约束：`graph` 层需要 numpy / networkx。为了让没有这两个包的环境也能起 API
（CI 的 contract 测试、本地最小安装），这里对 `graph.store` 全部**惰性导入**，
导入失败就退化为 fixture 只读，而不是让整个应用起不来。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ...common.config import fixture_path, get_settings
from ...common.errors import AppError, ErrorCode
from ...common.logging import get_logger
from ...common.schemas import GraphEdge, GraphNode, MechanismUnit, Subgraph

log = get_logger(__name__)

# 与 match.pipeline.load_corpus() 的兜底版本号保持一致，否则 health 会和 bridge 对不上
FIXTURE_VERSION = "fixtures"


@dataclass(frozen=True)
class Snapshot:
    """当前生效的一份图谱。store 为 None 表示只有机制列表、不能做邻域扩展。"""

    mechanisms: list[MechanismUnit]
    version: str
    source: str  # "index" | "fixture"
    store: Any | None = None
    nodes: list[GraphNode] | None = None
    edges: list[GraphEdge] | None = None


def _fixture_raw() -> dict[str, Any]:
    path = fixture_path("bridge.sample.json")
    if not path.exists():
        raise AppError(ErrorCode.GRAPH_NOT_READY, "图谱未构建且没有 fixture 兜底", 503)
    return json.loads(path.read_text(encoding="utf-8"))


def _fixture_mechanisms(raw: dict[str, Any]) -> list[MechanismUnit]:
    found = [MechanismUnit.model_validate(item) for item in raw.get("source", {}).get("mechanisms", [])]
    found.extend(
        MechanismUnit.model_validate(bridge["target_mechanism"]) for bridge in raw.get("bridges", [])
    )
    return found


def _import_store() -> Any | None:
    """惰性导入 GraphStore。没有 numpy/networkx 时返回 None。"""
    try:
        from ...graph.store import GraphStore
    except Exception as exc:  # ImportError 及依赖链上的任何问题
        log.warning("graph_store_unavailable", extra={"kv": {"err": type(exc).__name__}})
        return None
    return GraphStore


def _load_indexed(store_cls: Any) -> Snapshot | None:
    index = get_settings().resolved_data_dir / "index"
    if not index.is_dir():
        return None
    for path in sorted(index.iterdir(), reverse=True):
        if not (path / "graph.pkl").exists():
            continue
        try:
            store = store_cls.load(path)
        except Exception as exc:
            log.warning(
                "graph_load_failed",
                extra={"kv": {"snapshot": path.name, "err": type(exc).__name__}},
            )
            continue
        return Snapshot(
            mechanisms=store.all_mechanisms(),
            version=str(store.version),
            source="index",
            store=store,
        )
    return None


def _graph_from_mechanisms(mechanisms: list[MechanismUnit]) -> tuple[list[GraphNode], list[GraphEdge]]:
    """从机制列表构图，供 fixture 兜底的邻域扩展使用。

    只取 `bridge.sample.json` 的 source.subgraph 是不够的：桥接目标侧的概念不在里面，
    前端点目标节点依然会 404。这里两侧都建，语义与 GraphStore 一致。
    """
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    for mechanism in mechanisms:
        for ref in (mechanism.subject, mechanism.object):
            nodes.setdefault(
                ref.concept_id,
                GraphNode(
                    id=ref.concept_id,
                    label=ref.surface,
                    domain=mechanism.domain,
                    type=ref.type,
                ),
            )
        edges.append(
            GraphEdge(
                id=f"e:{mechanism.id}",
                source=mechanism.subject.concept_id,
                target=mechanism.object.concept_id,
                action_class=mechanism.action.action_class,
            )
        )
    return list(nodes.values()), edges


def _load_fixture() -> Snapshot:
    raw = _fixture_raw()
    mechanisms = _fixture_mechanisms(raw)
    nodes, edges = _graph_from_mechanisms(mechanisms)
    if not nodes:
        # 极端兜底：连机制都没有时退回样例里写死的子图
        nodes = [GraphNode.model_validate(n) for n in raw.get("source", {}).get("subgraph", {}).get("nodes", [])]
        edges = [GraphEdge.model_validate(e) for e in raw.get("source", {}).get("subgraph", {}).get("edges", [])]
    return Snapshot(
        mechanisms=mechanisms,
        version=FIXTURE_VERSION,
        source="fixture",
        nodes=nodes,
        edges=edges,
    )


@lru_cache(maxsize=1)
def current_snapshot() -> Snapshot:
    """当前生效快照。改动环境变量（如 DEMO_MODE）后需调 reset_snapshot_cache()。"""
    settings = get_settings()
    if not settings.demo_mode:
        store_cls = _import_store()
        if store_cls is not None:
            indexed = _load_indexed(store_cls)
            if indexed is not None:
                log.info(
                    "snapshot_indexed",
                    extra={"kv": {"version": indexed.version, "mechanisms": len(indexed.mechanisms)}},
                )
                return indexed
    fixture = _load_fixture()
    log.info("snapshot_fixture", extra={"kv": {"mechanisms": len(fixture.mechanisms)}})
    return fixture


def reset_snapshot_cache() -> None:
    current_snapshot.cache_clear()


def find_mechanism(mechanism_id: str) -> MechanismUnit:
    snapshot = current_snapshot()
    for mechanism in snapshot.mechanisms:
        if mechanism.id == mechanism_id:
            return mechanism
    raise AppError(
        ErrorCode.NOT_FOUND,
        f"机制 {mechanism_id} 不在当前图谱（版本 {snapshot.version}）",
        404,
    )


def _bfs_fixture(snapshot: Snapshot, concept_id: str, hops: int) -> Subgraph:
    nodes = snapshot.nodes or []
    edges = snapshot.edges or []
    if concept_id not in {node.id for node in nodes}:
        raise AppError(ErrorCode.NOT_FOUND, f"概念 {concept_id} 不在图中", 404)

    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.source, set()).add(edge.target)
        adjacency.setdefault(edge.target, set()).add(edge.source)

    keep = {concept_id}
    frontier = {concept_id}
    for _ in range(hops):
        frontier = {nxt for node in frontier for nxt in adjacency.get(node, set())} - keep
        if not frontier:
            break
        keep |= frontier
    return Subgraph(
        nodes=[node for node in nodes if node.id in keep],
        edges=[edge for edge in edges if edge.source in keep and edge.target in keep],
    )


def subgraph_for(concept_id: str, hops: int = 2) -> Subgraph:
    """按当前快照取邻域。真实图谱走 GraphStore，fixture 走本地 BFS。"""
    snapshot = current_snapshot()
    if snapshot.store is not None:
        found = snapshot.store.subgraph(concept_id, hops=hops)
        if not found.nodes:
            raise AppError(
                ErrorCode.NOT_FOUND,
                f"概念 {concept_id} 不在当前图谱（版本 {snapshot.version}）",
                404,
            )
        return found
    return _bfs_fixture(snapshot, concept_id, hops)


def snapshot_dir() -> Path | None:
    """调试用：当前索引快照目录（fixture 兜底时为 None）。"""
    snapshot = current_snapshot()
    if snapshot.source != "index":
        return None
    index = get_settings().resolved_data_dir / "index"
    for path in sorted(index.iterdir(), reverse=True):
        if (path / "graph.pkl").exists():
            return path
    return None
