"""命令行用 fixture 打出一份合法 BridgeResult。"""

from __future__ import annotations

from conceptbridge.common.schemas import BridgeResult
from conceptbridge.match.cli import main


def test_fixtures_flag_prints_bridge_result(capsys) -> None:
    code = main(["--query", "锂枝晶抑制", "--fixtures"])
    assert code == 0
    result = BridgeResult.model_validate_json(capsys.readouterr().out)
    assert result.meta.stub is False
    assert result.bridges
    assert result.query == "锂枝晶抑制"
