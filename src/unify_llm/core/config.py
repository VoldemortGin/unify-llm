"""兼容 shim:旧式(API-key 风格)Settings;无 import 时副作用(全部延迟到首次访问)。

正统配置入口已迁至 unify_llm.core.settings(叶子,beartype hook 前导入)。本模块仅为
兼容历史 `from unify_llm.core.config import settings/Settings/get_settings/load_yaml_config`
而保留;Phase 2+ 现代化后移除。该文件在 ratchet 豁免名单内,不受严格门约束。
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path | None:
    if root_env := os.environ.get("UNIFY_LLM_ROOT"):
        root_path = Path(root_env)
        if root_path.exists():
            return root_path
    cwd = Path.cwd()
    if (cwd / ".env").exists() or (cwd / "configs").exists():
        return cwd
    return None


@lru_cache(maxsize=1)
def _yaml_config() -> dict[str, Any]:
    root = _find_project_root()
    candidates = [
        Path(os.environ["UNIFY_LLM_CONFIG"]) if os.environ.get("UNIFY_LLM_CONFIG") else None,
        (root / "configs" / "config.yaml") if root else None,
        Path.cwd() / "configs" / "config.yaml",
        Path.home() / ".unify_llm" / "config.yaml",
    ]
    for path in candidates:
        if path and path.exists():
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    """旧式应用配置(API keys 等)。优先级:环境变量 > .env > 默认。"""

    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    XAI_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    QWEN_API_KEY: str | None = None
    DASHSCOPE_API_KEY: str | None = None
    BYTEDANCE_API_KEY: str | None = None

    DATABRICKS_API_KEY: str | None = None
    DATABRICKS_BASE_URL: str | None = None
    DATABRICKS_MODEL: str | None = None

    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT: float = 60.0
    LLM_MAX_RETRIES: int = 3

    OLLAMA_BASE_URL: str = "http://localhost:11434"

    APP_NAME: str = "UnifyLLM"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")

    def get_config(self, key: str, default: Any = None) -> Any:
        value: Any = _yaml_config()
        try:
            for part in key.split("."):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # 副作用延迟到首次访问:此处才 load_dotenv。
    load_dotenv()
    return Settings()


def load_yaml_config(config_path: str | Path | None = None) -> dict[str, Any]:
    if config_path is None:
        return _yaml_config()
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def __getattr__(name: str) -> Any:
    if name == "settings":
        return get_settings()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
