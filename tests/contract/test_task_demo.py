"""`task demo` 预检：真实语料检查的行为。

契约：
- 默认演示（冻结样例）即使没装真实语料也必须能启动，只提示不阻塞；
- `task demo --corpus` 明确要求真实语料，缺了必须硬失败，不能悄悄退回 4 条样例。
"""

from __future__ import annotations

import pytest

from conceptbridge.common.config import get_settings
from conceptbridge.task import _corpus_index, _demo_preflight


@pytest.fixture(autouse=True)
def _reset_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_corpus_index_is_none_without_data_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", ".no-such-index-dir-corpus")
    get_settings.cache_clear()
    assert _corpus_index() is None


def test_plain_demo_starts_without_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    """没装真实语料也要能演示——这是"绝不会开天窗"的底线。"""
    monkeypatch.setenv("DATA_DIR", ".no-such-index-dir-corpus")
    get_settings.cache_clear()
    assert _demo_preflight(corpus=False) == 0


def test_corpus_demo_fails_without_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    """显式要真实语料却拿不到时，必须拦住，而不是静默用样例糊过去。"""
    monkeypatch.setenv("DATA_DIR", ".no-such-index-dir-corpus")
    get_settings.cache_clear()
    assert _demo_preflight(corpus=True) == 1
