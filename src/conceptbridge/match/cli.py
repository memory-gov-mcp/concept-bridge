"""匹配命令行。`--fixtures` 只读样例，不碰 data/index。"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .pipeline import build_result, load_fixture_mechanisms, run_bridge


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="conceptbridge.match.cli")
    parser.add_argument("--query", required=True)
    parser.add_argument("--fixtures", action="store_true")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args(argv)
    if args.fixtures:
        result = asyncio.run(
            _from_fixtures(args.query, args.top_k),
        )
    else:
        result = asyncio.run(run_bridge(args.query, top_k=args.top_k))
    sys.stdout.write(result.model_dump_json(indent=2))
    sys.stdout.write("\n")
    return 0


async def _from_fixtures(query: str, top_k: int):
    return build_result(
        query,
        load_fixture_mechanisms(),
        None,
        top_k,
        None,
        graph_version="fixtures",
    )


if __name__ == "__main__":
    raise SystemExit(main())
