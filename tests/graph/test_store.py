"""GraphStore 持久化、加载与 N 跳子图。"""

from __future__ import annotations

import json
import time

from conceptbridge.common.config import fixture_path
from conceptbridge.common.schemas import MechanismUnit
from conceptbridge.graph.store import GraphStore


def load_sample_mechanisms() -> list[MechanismUnit]:
    raw = json.loads(fixture_path("bridge.sample.json").read_text(encoding="utf-8"))
    units = [MechanismUnit.model_validate(item) for item in raw["source"]["mechanisms"]]
    units.extend(
        MechanismUnit.model_validate(bridge["target_mechanism"]) for bridge in raw["bridges"]
    )
    return units


def test_save_load_and_one_hop(tmp_path) -> None:
    mechanisms = load_sample_mechanisms()
    store = GraphStore.from_mechanisms(mechanisms)
    dest = tmp_path / "g-20261102-0"
    store.save(dest)

    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["mechanism_count"] == len(mechanisms)
    assert manifest["git_sha"]
    assert (dest / "graph.pkl").exists()
    assert (dest / "embeddings.npy").exists()
    assert (dest / "mechanisms.jsonl").exists()

    loaded = GraphStore.load(dest)
    assert [item.id for item in loaded.all_mechanisms()] == [item.id for item in mechanisms]

    sub = loaded.subgraph("c_sei_film", hops=1)
    assert {node.id for node in sub.nodes} == {"c_sei_film", "c_li_ion_flux"}
    assert {edge.id for edge in sub.edges} == {"mu_01J9A2K7"}
    assert loaded.mechanisms_for({"c_sei_film"})[0].id == "mu_01J9A2K7"
    assert loaded.subgraph("missing", hops=1).nodes == []


def _synthetic(count: int) -> list[MechanismUnit]:
    template = load_sample_mechanisms()[0].model_dump()
    units: list[MechanismUnit] = []
    for index in range(count):
        data = json.loads(json.dumps(template))
        data["id"] = f"mu_syn_{index}"
        data["paper_id"] = f"W{index}"
        data["subject"]["concept_id"] = f"c_s_{index}"
        data["subject"]["surface"] = f"主体{index}"
        data["object"]["concept_id"] = f"c_o_{index}"
        data["object"]["surface"] = f"客体{index}"
        units.append(MechanismUnit.model_validate(data))
    return units


def test_five_hundred_mechanisms_build_and_load_within_budget(tmp_path) -> None:
    mechanisms = _synthetic(500)
    started = time.perf_counter()
    store = GraphStore.from_mechanisms(mechanisms)
    assert time.perf_counter() - started < 10

    dest = tmp_path / "g-bench"
    store.save(dest)
    started = time.perf_counter()
    loaded = GraphStore.load(dest)
    assert time.perf_counter() - started < 2
    assert len(loaded.all_mechanisms()) == 500
