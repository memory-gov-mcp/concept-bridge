"""契约测试：样例合法 + 已提交的契约产物与代码不漂移。

这两条是"技术实现 40%"里最便宜的保险：
- 契约漂移测试挂掉，说明有人改了模型没重新导出 → 前端会静默错位。
- 样例校验挂掉，说明 fixture 或抽取器产出了非法数据 → 演示当场崩。
"""

from __future__ import annotations

import yaml
from jsonschema import Draft202012Validator

from conceptbridge.common.config import REPO_ROOT


def test_sample_bridge_result_is_valid(committed_schemas, sample_result) -> None:
    schema = committed_schemas["bridge_result"]
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(sample_result), key=str)
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_all_schemas_are_valid_json_schema(committed_schemas) -> None:
    for schema in committed_schemas.values():
        Draft202012Validator.check_schema(schema)


def test_committed_schemas_match_code(committed_schemas) -> None:
    from conceptbridge.contracts_export import render_schemas

    for path, expected in render_schemas().items():
        actual = path.read_text(encoding="utf-8")
        assert actual == expected, f"{path.name} 与代码不一致，运行 uv run task contract"


def test_committed_openapi_matches_code() -> None:
    from conceptbridge.contracts_export import render_openapi

    for path, expected in render_openapi().items():
        actual = path.read_text(encoding="utf-8")
        assert actual == expected, f"{path.name} 与代码不一致，运行 uv run task contract"


def test_openapi_covers_required_paths() -> None:
    spec = yaml.safe_load((REPO_ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
    required = {
        "/api/v1/health",
        "/api/v1/bridge",
        "/api/v1/bridge/stream",
        "/api/v1/mechanisms/{mechanism_id}",
        "/api/v1/graph/subgraph",
        "/api/v1/eval/report",
        "/api/v1/feedback",
    }
    missing = required - set(spec["paths"])
    assert not missing, f"OpenAPI 缺少路径: {sorted(missing)}"
