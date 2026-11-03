"""OpenAlex 分页请求。离线测试通过 httpx.MockTransport 注入录制响应。"""

import time
from typing import Any

import httpx

QUERIES = (
    ("materials_science", "25", "lithium dendrite"),
    ("chemistry", "16", "ion transport"),
    ("biology", "13", "membrane ion channel"),
    ("medicine", "27", "immune regulation"),
    ("computer_science", "17", "swarm optimization"),
    ("physics", "31", "synchronization"),
)


def fetch_page(client: httpx.Client, params: dict[str, Any]) -> dict[str, Any]:
    for attempt in range(3):
        delay = 2**attempt
        try:
            response = client.get("https://api.openalex.org/works", params=params)
            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    delay = min(60, max(delay, int(retry_after)))
                response.raise_for_status()
            response.raise_for_status()
            page = response.json()
            if not isinstance(page, dict) or not isinstance(page.get("results"), list):
                raise ValueError("OpenAlex page lacks results")
            meta = page.get("meta")
            count = meta.get("count") if isinstance(meta, dict) else None
            if type(count) is not int or count < 0:
                raise ValueError("OpenAlex page lacks a valid count")
            return page
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 429 and exc.response.status_code < 500:
                raise
            if attempt == 2:
                raise
        except httpx.TransportError:
            if attempt == 2:
                raise
        time.sleep(delay)
    raise RuntimeError("unreachable retry state")
