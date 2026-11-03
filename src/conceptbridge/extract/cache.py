"""串行调用公共网关并记录可验证的请求用量。"""

import asyncio
from typing import Any

from ..common.llm import LLMClient


class CachedGateway:
    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self.semaphore = asyncio.Semaphore(1)
        self.stats = {"requests": 0, "cache_hits": 0, "gateway_calls": 0}

    async def complete(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.client.settings.llm_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.0,
            "max_tokens": 8192,
            "response_format": {"type": "json_object"},
        }
        async with self.semaphore:
            self.stats["requests"] += 1
            hit = self.client.read_cache(self.client.cache_key(payload))
            if hit is not None:
                self.stats["cache_hits"] += 1
                return hit
            self.stats["gateway_calls"] += 1
            return await self.client.complete_json(system=system, user=user, max_tokens=8192)
