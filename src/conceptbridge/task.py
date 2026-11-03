"""仓库任务入口：uv run task <命令>。

不用 make —— 本队四台机器都是 Windows，没有 make。
"""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import subprocess
import sys

from .common.config import REPO_ROOT

PY = sys.executable

# 子进程统一 UTF-8：否则 Windows 中文控制台（cp936）下 pytest / uvicorn 的中文全是乱码
_FORCE_UTF8 = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def _force_utf8_console() -> None:
    """把控制台代码页切到 65001 并把 stdout/stderr 设成 UTF-8。

    Windows 默认 cp936，Python 会按 GBK 打印，中文任务提示直接乱码。
    这件事必须在答辩演示前解决——现场看 `task demo` 出乱码，比功能少一个还难看。
    """
    if os.name == "nt":
        with contextlib.suppress(Exception):
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)  # type: ignore[attr-defined]
            ctypes.windll.kernel32.SetConsoleCP(65001)  # type: ignore[attr-defined]
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> int:
    print("$ " + " ".join(cmd), flush=True)
    merged = {**os.environ, **_FORCE_UTF8, **(env or {})}
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


# --------------------------------------------------------------------------- #
# 离线演示（P3-T6）
# --------------------------------------------------------------------------- #

# (路径, 说明, 是否硬依赖)
DEMO_ASSETS: tuple[tuple[str, str, bool], ...] = (
    ("fixtures/bridge.sample.json", "跨域桥兜底样例", True),
    ("contracts/openapi.yaml", "API 契约（前端按它对 mock）", True),
    ("contracts/schemas/bridge_result.json", "数据契约", True),
    ("eval/gold/analogy_pairs.jsonl", "金标准（答辩讲评测要用）", True),
    ("eval/reports/latest.json", "评测报告（缺了只影响评测页）", False),
)


def _demo_preflight() -> int:
    """演示前把能检查的都检查掉。现场少一次意外，比多一个功能值。"""
    print("== 离线演示预检（DEMO_MODE=1，禁止外网）==")
    hard_missing: list[str] = []
    soft_missing: list[str] = []
    for rel, desc, hard in DEMO_ASSETS:
        exists = (REPO_ROOT / rel).exists()
        print(f"  [{'OK  ' if exists else 'MISS'}] {rel:<36} {desc}")
        if not exists:
            (hard_missing if hard else soft_missing).append(rel)

    if soft_missing:
        print("\n  ! 缺评测报告：答辩前跑一次 `uv run task eval`，否则 /eval/report 是空的")

    if hard_missing:
        print("\n[预检失败] 必需资产缺失：" + ", ".join(hard_missing))
        return 1

    print("\n[预检通过] 可以拔网线演示。")
    return 0


def cmd_demo() -> int:
    if _demo_preflight() != 0:
        return 1
    print("\n地址 http://127.0.0.1:8000/docs   （Ctrl+C 退出）\n")
    return _run(
        [PY, "-m", "uvicorn", "conceptbridge.api.main:app", "--port", "8000"],
        env={"DEMO_MODE": "1"},
    )


def cmd_merge() -> int:
    """合并窗口的闸门：check 必须绿，e2e 必须过，否则不许合入 main。"""
    print("== 合并门禁 ==")
    if cmd_check() != 0:
        print("\n[禁止合并] check 未通过")
        return 1
    if cmd_e2e() != 0:
        print("\n[禁止合并] e2e 未通过")
        return 1
    print("\n[可以合并] check + e2e 全绿")
    return 0


def cmd_freeze(tag: str | None = None) -> int:
    tag = tag or "v0.9-submit"
    return _run(["git", "tag", "-a", tag, "-m", f"freeze {tag}"])


COMMANDS = {
    "setup": cmd_setup,
    "contract": cmd_contract,
    "check": cmd_check,
    "merge": cmd_merge,
    "e2e": cmd_e2e,
    "eval": cmd_eval,
    "dev": cmd_dev,
    "demo": cmd_demo,
    "freeze": cmd_freeze,
}


def main(argv: list[str] | None = None) -> int:
    _force_utf8_console()
    parser = argparse.ArgumentParser(prog="task", description="ConceptBridge 任务入口")
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("arg", nargs="?", default=None, help="可选参数（如 freeze 的 tag）")
    ns = parser.parse_args(argv)
    if ns.command == "freeze":
        return cmd_freeze(ns.arg)
    return COMMANDS[ns.command]()


if __name__ == "__main__":
    raise SystemExit(main())
