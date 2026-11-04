"""match 测试的隔离夹具。

与 `tests/api/conftest.py` 同因：`match` 的用例断言的是 fixture 语料下的行为
（两个领域、两条桥、排除 biology 后为空）。本机一旦装了 `data/index/g-*`，
`load_corpus()` 会切到真实语料，这些断言的领域与条数就对不上——
CI 上没索引所以绿，本机装了索引就红，属于"看环境变色"的测试。

统一把 DATA_DIR 指到不存在的路径，强制走 fixture。真实索引路径由 e2e 覆盖。
"""

from __future__ import annotations

import pytest

from conceptbridge.api.services.snapshot import reset_snapshot_cache
from conceptbridge.common.config import get_settings


@pytest.fixture(autouse=True)
def isolate_fixture_snapshot(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATA_DIR", ".no-index-for-match-tests")
    get_settings.cache_clear()
    reset_snapshot_cache()
    yield
    get_settings.cache_clear()
    reset_snapshot_cache()
