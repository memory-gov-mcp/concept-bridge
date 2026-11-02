"""FastAPI 入口。契约以本 app 生成的 openapi.yaml 为准。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..common.config import get_settings
from ..common.errors import register_exception_handlers
from ..common.logging import configure_logging
from .routes import bridge, evaluate, feedback, graph, health, mechanisms


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
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    for module in (health, bridge, mechanisms, graph, evaluate, feedback):
        app.include_router(module.router, prefix="/api/v1")

    return app


app = create_app()
