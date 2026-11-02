"""测试共享夹具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from conceptbridge.common.config import REPO_ROOT


@pytest.fixture(scope="session")
def sample_result() -> dict[str, Any]:
    path = REPO_ROOT / "fixtures" / "bridge.sample.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def committed_schemas() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for p in sorted((REPO_ROOT / "contracts" / "schemas").glob("*.json")):
        out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return out


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")
