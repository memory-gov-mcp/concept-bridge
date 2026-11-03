"""FastAPI 依赖注入。

目前只暴露配置。P2 的图存储接进来时在这里加 `get_store()`，
这样路由层不用知道构造细节，也方便测试时替换。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from ..common.config import Settings, get_settings


def settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dep)]
