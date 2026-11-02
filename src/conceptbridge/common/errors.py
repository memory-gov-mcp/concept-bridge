"""错误码与 FastAPI 异常处理。前端按 code 出人话文案（AGENTS.md §9）。"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .logging import get_logger
from .schemas import ErrorBody

log = get_logger(__name__)


class ErrorCode(str, Enum):
    BAD_REQUEST = "BAD_REQUEST"
    QUERY_TOO_SHORT = "QUERY_TOO_SHORT"
    GRAPH_NOT_READY = "GRAPH_NOT_READY"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL = "INTERNAL"


class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _body(code: str, message: str, trace_id: str) -> dict[str, Any]:
    return ErrorBody(code=code, message=message, trace_id=trace_id).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        trace_id = uuid.uuid4().hex[:12]
        log.warning("app_error", extra={"kv": {"code": exc.code.value, "trace_id": trace_id}})
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.code.value, exc.message, trace_id),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        trace_id = uuid.uuid4().hex[:12]
        log.exception("unhandled", extra={"kv": {"trace_id": trace_id, "err": type(exc).__name__}})
        return JSONResponse(
            status_code=500,
            content=_body(ErrorCode.INTERNAL.value, "服务内部错误，请重试", trace_id),
        )
