"""图谱持久化。load 只读 pickle 与 npy，不重建向量模型。"""

from __future__ import annotations

import json
import pickle
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx
import numpy as np

from ..common.config import REPO_ROOT
from ..common.logging import get_logger
from ..common.schemas import GraphEdge, GraphNode, MechanismUnit, Subgraph
from .builder import BuiltGraph, build_graph
from .embeddings import hash_embed

log = get_logger(__name__)


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return out.strip() or "unknown"


class GraphStore:
    """概念点 + 机制边。邻域按无向跳数扩展，平行边全部保留。"""

    def __init__(
        self,
        mechanisms: list[MechanismUnit],
        built: BuiltGraph,
        embeddings: np.ndarray,
        version: str,
    ) -> None:
        self._mechanisms = list(mechanisms)
        self._built = built
        self._embeddings = embeddings
        self.version = version
        self._by_concept: dict[str, list[MechanismUnit]] = {}
        for mechanism in self._mechanisms:
            for concept_id in (mechanism.subject.concept_id, mechanism.object.concept_id):
                self._by_concept.setdefault(concept_id, []).append(mechanism)

    @classmethod
    def from_mechanisms(cls, mechanisms: list[MechanismUnit], *, version: str = "g-local") -> GraphStore:
        built = build_graph(mechanisms)
        texts = [
            " ".join([mechanism.action.verb, *mechanism.conditions, mechanism.result])
            for mechanism in mechanisms
        ]
        return cls(mechanisms, built, hash_embed(texts), version)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "graph": self._built.graph,
            "nodes": [node.model_dump() for node in self._built.nodes],
            "edges": [edge.model_dump() for edge in self._built.edges],
            "version": self.version,
        }
        with (directory / "graph.pkl").open("wb") as handle:
            pickle.dump(payload, handle)
        lines = [mechanism.model_dump_json() for mechanism in self._mechanisms]
        body = ("\n".join(lines) + "\n") if lines else ""
        (directory / "mechanisms.jsonl").write_text(body, encoding="utf-8")
        np.save(directory / "embeddings.npy", self._embeddings)
        manifest = {
            "git_sha": _git_sha(),
            "mechanism_count": len(self._mechanisms),
            "node_count": len(self._built.nodes),
            "graph_version": directory.name,
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        (directory / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info(
            "graph_saved",
            extra={"kv": {"version": directory.name, "mechanisms": len(self._mechanisms)}},
        )

    @classmethod
    def load(cls, path: Path) -> GraphStore:
        with (path / "graph.pkl").open("rb") as handle:
            payload = pickle.load(handle)
        mechanisms: list[MechanismUnit] = []
        raw = (path / "mechanisms.jsonl").read_text(encoding="utf-8")
        for line in raw.splitlines():
            if line.strip():
                mechanisms.append(MechanismUnit.model_validate_json(line))
        embeddings = np.load(path / "embeddings.npy")
        built = BuiltGraph(
            nodes=[GraphNode.model_validate(node) for node in payload["nodes"]],
            edges=[GraphEdge.model_validate(edge) for edge in payload["edges"]],
            graph=payload["graph"],
        )
        return cls(mechanisms, built, embeddings, str(payload["version"]))

    def subgraph(self, concept_id: str, hops: int = 2) -> Subgraph:
        if concept_id not in self._built.graph:
            return Subgraph()
        keep = set(nx.single_source_shortest_path_length(self._built.graph, concept_id, cutoff=hops))
        nodes = [node for node in self._built.nodes if node.id in keep]
        edges = [
            edge for edge in self._built.edges if edge.source in keep and edge.target in keep
        ]
        return Subgraph(nodes=nodes, edges=edges)

    def mechanisms_for(self, concept_ids: set[str]) -> list[MechanismUnit]:
        seen: set[str] = set()
        found: list[MechanismUnit] = []
        for concept_id in concept_ids:
            for mechanism in self._by_concept.get(concept_id, []):
                if mechanism.id in seen:
                    continue
                seen.add(mechanism.id)
                found.append(mechanism)
        return found

    def all_mechanisms(self) -> list[MechanismUnit]:
        return list(self._mechanisms)
