"""导出契约产物：contracts/schemas/*.json 与 contracts/openapi.yaml。

单一来源是 Pydantic 模型与 FastAPI app，因此契约不会和代码漂移。
`uv run task check` 里有测试会重新生成一遍并和已提交文件逐字节比对。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .common.config import REPO_ROOT
from .common.schemas import BridgeResult, EvalReport, MechanismUnit

SCHEMA_MODELS: dict[str, Any] = {
    "mechanism_unit": MechanismUnit,
    "bridge_result": BridgeResult,
    "eval_report": EvalReport,
}

CONTRACTS_DIR = REPO_ROOT / "contracts"


def render_schemas() -> dict[Path, str]:
    out: dict[Path, str] = {}
    for name, model in SCHEMA_MODELS.items():
        schema = model.model_json_schema()
        text = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        out[CONTRACTS_DIR / "schemas" / f"{name}.json"] = text
    return out


def render_openapi() -> dict[Path, str]:
    # 延迟导入：避免测试只想要 schema 时也去初始化 FastAPI
    from .api.main import app

    spec = app.openapi()
    text = yaml.safe_dump(spec, allow_unicode=True, sort_keys=True, width=1000)
    return {CONTRACTS_DIR / "openapi.yaml": text}


def export_all(write: bool = True) -> dict[Path, str]:
    artifacts = {**render_schemas(), **render_openapi()}
    if write:
        for path, text in artifacts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    return artifacts
