"""统一 LLM 网关（OpenAI 兼容）。

规则（AGENTS.md §12.1）：
- 全项目只允许通过本模块调 LLM，禁止各处裸调 httpx。
- 所有调用必须走磁盘缓存，保证评测与演示可复现。
- DEMO_MODE=1 时只读缓存，不回源。
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import Settings, get_settings
from .errors import AppError, ErrorCode
from .logging import get_logger

log = get_logger(__name__)


class LLMUnavailable(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.LLM_UNAVAILABLE, message, status_code=503)


class _Transient(Exception):
    """可重试的上游错误。"""


class LLMClient:
    def __init__(self, settings: Settings | None = None, cache_dir: Path | None = None) -> None:
        self.settings = settings or get_settings()
        self.cache_dir = cache_dir or self.settings.llm_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.usage_path = self.cache_dir / "_usage.json"

    # ------------------------------------------------------------------ #
    # 缓存
    # ------------------------------------------------------------------ #

    def cache_key(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def _cache_file(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def read_cache(self, key: str) -> dict[str, Any] | None:
        p = self._cache_file(key)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def write_cache(self, key: str, response: dict[str, Any]) -> None:
        p = self._cache_file(key)
        p.write_text(
            json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _note_usage(self, prompt_chars: int, completion_chars: int) -> None:
        """只记录用量，不做预算拦截（团队决定：本赛程不考虑预算）。"""
        data: dict[str, Any] = {"calls": 0, "prompt_chars": 0, "completion_chars": 0}
        if self.usage_path.exists():
            with contextlib.suppress(json.JSONDecodeError):
                data = json.loads(self.usage_path.read_text(encoding="utf-8"))
        data["calls"] += 1
        data["prompt_chars"] += prompt_chars
        data["completion_chars"] += completion_chars
        self.usage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # 调用
    # ------------------------------------------------------------------ #

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        model: str | None = None,
        max_tokens: int = 2048,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        model = model or self.settings.llm_model
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        key = self.cache_key(payload)

        if use_cache:
            hit = self.read_cache(key)
            if hit is not None:
                log.debug("llm_cache_hit", extra={"kv": {"key": key}})
                return hit

        if self.settings.demo_mode or self.settings.llm_offline:
            mode = "DEMO_MODE" if self.settings.demo_mode else "LLM_OFFLINE"
            raise LLMUnavailable(f"{mode} 下缓存未命中（key={key}）")

        if not self.settings.llm_api_key:
            raise LLMUnavailable("未配置 LLM_API_KEY，见 .env.example")

        raw = await self._post(payload)
        if use_cache:
            self.write_cache(key, raw)
        self._note_usage(len(system) + len(user), len(json.dumps(raw)))
        return raw

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        started = time.perf_counter()
        try:
            content = await self._post_with_retry(url, headers, payload)
        except _Transient as exc:
            raise LLMUnavailable(f"LLM 上游失败: {exc}") from exc
        log.info(
            "llm_call",
            extra={"kv": {"ms": int((time.perf_counter() - started) * 1000)}},
        )
        return content

    @retry(
        retry=retry_if_exception_type(_Transient),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.8, max=8),
        reraise=True,
    )
    async def _post_with_retry(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise _Transient(str(exc)) from exc

        if resp.status_code in (429, 500, 502, 503, 504):
            raise _Transient(f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            raise AppError(
                ErrorCode.BAD_REQUEST,
                f"LLM 返回 {resp.status_code}: {resp.text[:200]}",
                status_code=502,
            )
        body = resp.json()
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise AppError(ErrorCode.INTERNAL, "LLM 响应结构异常", status_code=502) from exc
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _Transient(f"JSON 解析失败: {text[:120]}") from exc
        if not isinstance(parsed, dict):
            raise _Transient("LLM 返回的不是 JSON 对象")
        return parsed

    def complete_json_sync(self, **kwargs: Any) -> dict[str, Any]:
        """给脚本 / CLI 用的同步包装。不要在已有事件循环里调用。"""
        return asyncio.run(self.complete_json(**kwargs))
