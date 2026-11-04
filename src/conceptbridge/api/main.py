"""FastAPI 入口。契约以本 app 生成的 openapi.yaml 为准。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..common.config import get_settings
from ..common.errors import register_exception_handlers
from ..common.logging import configure_logging
from .routes import bridge, evaluate, feedback, graph, health, mechanisms

# 离线极简界面：自包含 HTML，不依赖 node_modules 与构建产物。
# 用途：前端依赖装不上（断网 / CI 缓存失效）时，仍能在浏览器里看到双域桥。
FALLBACK_UI = Path(__file__).parent / "static" / "fallback.html"

_PLAIN_UI = (
    "<!doctype html><meta charset='utf-8'>"
    "<h1>ConceptBridge</h1>"
    "<p>API 可用。接口文档见 <a href='/docs'>/docs</a>。</p>"
)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="ConceptBridge API",
        version="0.1.0",
        description=(
            "输入领域 A 的难题，从领域 B 的文献检索结构相似的机制，"
            "返回可迁移假设、差异说明与原文出处。"
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    for module in (health, bridge, mechanisms, graph, evaluate, feedback):
        app.include_router(module.router, prefix="/api/v1")

    # include_in_schema=False：这是运维兜底页，不属于对外契约，不写进 openapi.yaml
    @app.get("/", include_in_schema=False)
    def offline_ui() -> HTMLResponse:
        if FALLBACK_UI.exists():
            return HTMLResponse(FALLBACK_UI.read_text(encoding="utf-8"))
        return HTMLResponse(_PLAIN_UI)

    return app


app = create_app()
