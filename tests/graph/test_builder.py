"""机制变成概念点、机制边。"""

from __future__ import annotations

import json

from conceptbridge.common.config import fixture_path
from conceptbridge.common.schemas import MechanismUnit
from conceptbridge.graph.builder import build_graph


def load_sample_mechanisms() -> list[MechanismUnit]:
    raw = json.loads(fixture_path("bridge.sample.json").read_text(encoding="utf-8"))
    units = [MechanismUnit.model_validate(item) for item in raw["source"]["mechanisms"]]
    units.extend(
        MechanismUnit.model_validate(bridge["target_mechanism"]) for bridge in raw["bridges"]
    )
    return units


def test_concepts_are_nodes_and_mechanisms_are_edges() -> None:
    built = build_graph(load_sample_mechanisms())
    node_ids = {node.id for node in built.nodes}
    assert "c_sei_film" in node_ids
    assert "c_plasma_membrane" in node_ids

    sei = next(edge for edge in built.edges if edge.id == "mu_01J9A2K7")
    assert sei.source == "c_sei_film"
    assert sei.target == "c_li_ion_flux"
    assert sei.action_class == "transport"
    assert len(built.edges) == 4
