"""run_bridge 在 fixture 语料上返回合法、非 stub 的桥。"""

from __future__ import annotations

import asyncio

from conceptbridge.common.schemas import BridgeResult
from conceptbridge.match.pipeline import run_bridge

DEMO_QUERIES = ["锂枝晶抑制", "催化剂失活", "蛋白质折叠"]


def test_demo_queries_return_cited_bridges() -> None:
    for query in DEMO_QUERIES:
        result = asyncio.run(run_bridge(query, top_k=3))
        checked = BridgeResult.model_validate(result.model_dump())
        assert checked.query == query
        assert checked.meta.stub is False
        assert checked.bridges
        assert checked.meta.candidates >= len(checked.bridges)
        for bridge in checked.bridges:
            assert bridge.target_domain != checked.source.domain
            roles = {item.source_role for item in bridge.alignment}
            assert {"subject", "object"} <= roles
            assert bridge.citations[0].span == bridge.target_mechanism.evidence.span


def test_top_k_and_exclude_domains() -> None:
    one = asyncio.run(run_bridge("锂枝晶抑制", top_k=1))
    assert len(one.bridges) == 1
    excluded = asyncio.run(run_bridge("锂枝晶抑制", exclude_domains=["biology"]))
    assert excluded.bridges == []
    assert excluded.meta.stub is False
