"""仓库任务入口：uv run task <命令>。

不用 make —— 本队四台机器都是 Windows，没有 make。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

from .common.config import REPO_ROOT

PY = sys.executable


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> int:
    print("$ " + " ".join(cmd), flush=True)
    merged = {**os.environ, **(env or {})}
    return subprocess.run(cmd, cwd=REPO_ROOT, env=merged, check=False).returncode


def _tool(name: str, *args: str) -> list[str]:
    exe = shutil.which(name)
    if exe:
        return [exe, *args]
    return [PY, "-m", name, *args]


def _has_web() -> bool:
    return (REPO_ROOT / "web" / "package.json").exists()


def _has_eval() -> bool:
    return (REPO_ROOT / "eval" / "run_eval.py").exists()


# --------------------------------------------------------------------------- #
# 命令
# --------------------------------------------------------------------------- #


def cmd_setup() -> int:
    uv = shutil.which("uv") or "uv"
    code = _run([uv, "sync", "--extra", "analyze", "--extra", "dev"])
    if code != 0:
        return code
    if _has_web() and shutil.which("npm"):
        return _run(["npm", "install", "--prefix", "web"])
    return 0


def cmd_contract() -> int:
    from .contracts_export import export_all

    artifacts = export_all(write=True)
    for path in sorted(artifacts):
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    return 0


def cmd_check() -> int:
    steps: list[tuple[str, list[str]]] = [
        ("ruff", _tool("ruff", "check", ".")),
        ("mypy", _tool("mypy")),
        ("pytest", _tool("pytest", "tests", "-q", "--ignore=tests/e2e")),
    ]
    failed: list[str] = []
    for name, cmd in steps:
        if _run(cmd) != 0:
            failed.append(name)
    if (
        _has_web()
        and shutil.which("npm")
        and _run(["npm", "--prefix", "web", "run", "typecheck"]) != 0
    ):
        failed.append("web:typecheck")
    if failed:
        print("\n[check] FAILED: " + ", ".join(failed))
        return 1
    print("\n[check] OK")
    return 0


def cmd_e2e() -> int:
    return _run(_tool("pytest", "tests/e2e", "-q"))


def cmd_eval() -> int:
    if not _has_eval():
        print("eval/run_eval.py 还没由 P2 落地（任务卡 P2-T5）")
        return 1
    return _run([PY, "eval/run_eval.py"])


def cmd_dev() -> int:
    return _run([PY, "-m", "uvicorn", "conceptbridge.api.main:app", "--reload", "--port", "8000"])


def cmd_demo() -> int:
    return _run(
        [PY, "-m", "uvicorn", "conceptbridge.api.main:app", "--port", "8000"],
        env={"DEMO_MODE": "1"},
    )


def cmd_freeze() -> int:
    tag = sys.argv[2] if len(sys.argv) > 2 else "v0.9-submit"
    return _run(["git", "tag", "-a", tag, "-m", f"freeze {tag}"])


COMMANDS = {
    "setup": cmd_setup,
    "contract": cmd_contract,
    "check": cmd_check,
    "e2e": cmd_e2e,
    "eval": cmd_eval,
    "dev": cmd_dev,
    "demo": cmd_demo,
    "freeze": cmd_freeze,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="task", description="ConceptBridge 任务入口")
    parser.add_argument("command", choices=sorted(COMMANDS))
    ns = parser.parse_args(argv)
    return COMMANDS[ns.command]()


if __name__ == "__main__":
    raise SystemExit(main())
