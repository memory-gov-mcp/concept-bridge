"""运行配置。所有环境变量只在这里读，业务代码不许直接读 os.environ。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/conceptbridge/common/config.py -> parents[3] 是仓库根
REPO_ROOT: Path = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openalex_mailto: str = "team@example.com"

    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"

    embed_model: str = "intfloat/multilingual-e5-large"

    data_dir: Path = Path("./data")
    demo_mode: bool = False
    top_k: int = 5
    bridge_timeout_s: float = 15.0
    log_level: str = "INFO"

    @property
    def resolved_data_dir(self) -> Path:
        p = self.data_dir
        return p if p.is_absolute() else (REPO_ROOT / p).resolve()

    @property
    def llm_cache_dir(self) -> Path:
        return self.resolved_data_dir / "llm_cache"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def fixture_path(name: str) -> Path:
    return REPO_ROOT / "fixtures" / name


def contract_path(name: str) -> Path:
    return REPO_ROOT / "contracts" / name
