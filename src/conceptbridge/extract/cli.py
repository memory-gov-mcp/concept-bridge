"""默认只运行八篇试验，扩量与重抽均需显式参数。"""

import argparse
import asyncio
import sqlite3

from ..common.config import get_settings
from ..common.errors import AppError
from ..common.logging import configure_logging, get_logger
from .pipeline import preview, run

log = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="机制抽取（默认 8 篇，零自动重抽）")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--retries", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="只显示输入规模，不调用模型")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be positive")
    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        if args.dry_run:
            log.info("extract_preview", extra={"kv": preview(settings, args.limit)})
            return 0
        report = asyncio.run(
            run(settings, limit=args.limit, retries=args.retries, retry_failed=args.retry_failed)
        )
    except (AppError, OSError, ValueError, sqlite3.Error) as exc:
        log.error("extract_failed", extra={"kv": {"error": type(exc).__name__}})
        return 1
    log.info(
        "extract_complete",
        extra={
            "kv": {
                "papers": report["paper_count"],
                "mechanisms": report["mechanism_count"],
                "failed_papers": report["failed_papers"],
                "usage": report["usage"],
            }
        },
    )
    return int(report["failed_papers"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
