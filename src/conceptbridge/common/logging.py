"""统一日志。禁止在库里 print，一律 get_logger(__name__)。"""

from __future__ import annotations

import logging
import sys


class _LineFormatter(logging.Formatter):
    """[module] [event] key=value —— 与 AGENTS.md §18.2 一致。"""

    def format(self, record: logging.LogRecord) -> str:
        module = record.name.rsplit(".", 1)[-1]
        event = record.getMessage()
        extra = getattr(record, "kv", None)
        if extra:
            kv = " ".join(f"{k}={v}" for k, v in extra.items())
            return f"[{module}] [{event}] {kv}"
        return f"[{module}] [{event}]"


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_LineFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
