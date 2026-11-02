"""匹配入口。这个模块可导入之后，API 会从 fixture stub 切到这里。"""

from __future__ import annotations

import json
import time

from ..common.config import fixture_path, get_settings
from ..common.logging import get_logger
from ..common.schemas import (
    Bridge,
    BridgeResult,
    BridgeSource,
    MechanismUnit,
    ResultMeta,
    Subgraph,
)
from ..graph.builder import build_graph
from ..graph.store import GraphStore
from .candidate import rank_candidates, select_sources
from .explain import explain_bridge

log = get_logger(__name__)


def load_fixture_mechanisms() -> list[MechanismUnit]:
    raw = json.loads(fixture_path("bridge.sample.json").read_text(encoding="utf-8"))
    units = [MechanismUnit.model_validate(item) for item in raw["source"]["mechanisms"]]
    units.extend(
        MechanismUnit.model_validate(bridge["target_mechanism"]) for bridge in raw["bridges"]
    )
    return units


def load_corpus() -> tuple[list[MechanismUnit], str]:
    """有持久化图谱就用最新一份，否则用 fixture。单测和 CI 走后者。"""
    index = get_settings().resolved_data_dir / "index"
    if index.is_dir():
        snapshots = sorted(path for path in index.iterdir() if (path / "graph.pkl").exists())
        if snapshots:
            store = GraphStore.load(snapshots[-1])
            return store.all_mechanisms(), store.version
    return load_fixture_mechanisms(), "fixtures"


def build_result(
    query: str,
    mechanisms: list[MechanismUnit],
    source_domain: str | None,
    top_k: int,
    exclude_domains: list[str] | None,
    *,
    graph_version: str,
) -> BridgeResult:
    started = time.perf_counter()
    sources = select_sources(query, mechanisms, source_domain)
    ranked, considered = rank_candidates(
        sources,
        mechanisms,
        exclude_domains=exclude_domains,
        top_k=top_k,
    )
    domain = sources[0].domain if sources else "unknown"
    built = build_graph(sources)
    bridges = []
    for pair in ranked:
        explained = explain_bridge(pair.source, pair.target)
        bridges.append(
            Bridge(
                target_mechanism=pair.target,
                target_domain=pair.target.domain,
                scores=pair.scores,
                alignment=explained.alignment,
                transferable_hypothesis=explained.hypothesis,
                differences=explained.differences,
                citations=explained.citations,
            )
        )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    result = BridgeResult(
        query=query,
        source=BridgeSource(
            domain=domain,
            mechanisms=sources,
            subgraph=Subgraph(nodes=built.nodes, edges=built.edges),
        ),
        bridges=bridges,
        meta=ResultMeta(
            latency_ms=elapsed_ms,
            candidates=max(considered, len(bridges)),
            graph_version=graph_version,
            degraded=False,
            stub=False,
        ),
    )
    log.info(
        "bridge_ready",
        extra={"kv": {"bridges": len(bridges), "candidates": considered, "latency_ms": elapsed_ms}},
    )
    return result


async def run_bridge(
    query: str,
    source_domain: str | None = None,
    top_k: int = 5,
    exclude_domains: list[str] | None = None,
) -> BridgeResult:
    mechanisms, version = load_corpus()
    return build_result(query, mechanisms, source_domain, top_k, exclude_domains, graph_version=version)
