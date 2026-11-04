"""API 测试的隔离夹具。

API 测试断言的是"fixture 样本下的行为"（例如 `mu_01J9A2K7` 这条机制、两个领域）。
但 `data/index/g-*` 一旦装在本机，快照就会切换到真实语料，断言 ID 和领域全部对不上——
CI 上没装索引所以一直是绿的，本机装了就会红，这种"看环境变色"的测试必须消除。

所以统一把 DATA_DIR 指到一个不存在的相对路径，强制走 fixture 快照。
真实索引路径由 `tests/match` 与 e2e 覆盖。
"""

from __future__ import annotations

import pytest

from conceptbridge.api.services.snapshot import reset_snapshot_cache
from conceptbridge.common.config import get_settings


@pytest.fixture(autouse=True)
def isolate_fixture_snapshot(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATA_DIR", ".no-index-for-api-tests")
    get_settings.cache_clear()
    reset_snapshot_cache()
    yield
    get_settings.cache_clear()
    reset_snapshot_cache()
