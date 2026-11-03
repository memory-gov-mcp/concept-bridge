"""Regression tests for the split between backend CI and local checks."""

from pathlib import Path

import pytest

from conceptbridge import task


@pytest.mark.parametrize(("github_actions", "expected_exit"), [("true", 0), (None, 1)])
def test_check_only_invokes_frontend_locally(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    github_actions: str | None,
    expected_exit: int,
) -> None:
    if github_actions is None:
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    else:
        monkeypatch.setenv("GITHUB_ACTIONS", github_actions)
    web = tmp_path / "web"
    web.mkdir()
    (web / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(task, "REPO_ROOT", tmp_path)
    npm = str(tmp_path / "npm.cmd")
    monkeypatch.setattr(task.shutil, "which", lambda name: npm if name == "npm" else name)

    commands: list[list[str]] = []

    def run(command: list[str]) -> int:
        commands.append(command)
        return int(command[-1] == "typecheck")

    monkeypatch.setattr(task, "_run", run)

    assert task.cmd_check() == expected_exit
    assert [command[0] for command in commands[:3]] == ["ruff", "mypy", "pytest"]
    frontend = [[npm, "--prefix", "web", "run", "typecheck"]]
    assert commands[3:] == ([] if github_actions else frontend)
