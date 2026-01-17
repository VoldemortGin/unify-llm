"""
Configuration management for UnifyLLM.

Simple settings management using pydantic-settings.
Supports loading from environment variables and optional YAML config file.
"""


from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path | None:
    """
    Try to find project root directory.
    Works in both development mode (with .project-root) and installed mode.
    """
    # 1. Check environment variable
    if root_env := os.environ.get("UNIFY_LLM_ROOT"):
        root_path = Path(root_env)
        if root_path.exists():
            return root_path

    # 2. Try rootutils (development mode)
    try:
        import rootutils

        return rootutils.find_root(search_from=os.getcwd(), indicator=[".project-root"])
    except (ImportError, FileNotFoundError):
        pass

    # 3. Check current working directory for .env or configs/
    cwd = Path.cwd()
    if (cwd / ".env").exists() or (cwd / "configs").exists():
        return cwd

    return None


# Setup root directory (may be None in installed mode)
ROOT_DIR = _find_project_root()

# Load .env file if exists
if ROOT_DIR:
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)
else:
    # Try loading from current directory or user home
    for env_path in [Path.cwd() / ".env", Path.home() / ".unify_llm" / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break

# Load optional YAML config
YAML_CONFIG: dict[str, Any] = {}
config_paths = [
    Path(os.environ.get("UNIFY_LLM_CONFIG", "")) if os.environ.get("UNIFY_LLM_CONFIG") else None,
    ROOT_DIR / "configs" / "config.yaml" if ROOT_DIR else None,
    Path.cwd() / "configs" / "config.yaml",
    Path.home() / ".unify_llm" / "config.yaml",
]
for config_path in config_paths:
    if config_path and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            YAML_CONFIG = yaml.safe_load(f) or {}
        break


class Settings(BaseSettings):
    """
    Application settings.

    Priority: environment variables > .env file > YAML config > defaults

    Example .env:
        OPENAI_API_KEY=sk-...
        ANTHROPIC_API_KEY=sk-ant-...
        GOOGLE_API_KEY=...
        OLLAMA_BASE_URL=http://localhost:11434
    """

    # LLM API Keys (from environment)
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

    # LLM Settings
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT: float = 60.0
    LLM_MAX_RETRIES: int = 3

    # Ollama Settings (for local models)
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Application Settings
    APP_NAME: str = "UnifyLLM"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Apply YAML config values for unset fields
        self._apply_yaml_defaults()

        # Set root directory (may be None in installed mode)
        self.root_dir = str(ROOT_DIR) if ROOT_DIR else str(Path.cwd())

    def _apply_yaml_defaults(self) -> None:
        """Apply default values from YAML config for fields that are not set."""
        if not YAML_CONFIG:
            return

        llm_config = YAML_CONFIG.get("llm", {})
        app_config = YAML_CONFIG.get("app", {})

        # LLM settings from YAML
        if self.LLM_TEMPERATURE == 0.7:  # default value
            self.LLM_TEMPERATURE = llm_config.get("temperature", 0.7)
        if self.LLM_MAX_TOKENS == 4096:
            self.LLM_MAX_TOKENS = llm_config.get("max_tokens", 4096)
        if self.LLM_TIMEOUT == 60.0:
            self.LLM_TIMEOUT = llm_config.get("timeout", 60.0)
        if self.LLM_MAX_RETRIES == 3:
            self.LLM_MAX_RETRIES = llm_config.get("max_retries", 3)
        if self.OLLAMA_BASE_URL == "http://localhost:11434":
            self.OLLAMA_BASE_URL = llm_config.get("ollama_base_url", "http://localhost:11434")

        # App settings from YAML
        if self.APP_NAME == "UnifyLLM":
            self.APP_NAME = app_config.get("name", "UnifyLLM")
        if self.DEBUG is False:
            self.DEBUG = app_config.get("debug", False)
        if self.LOG_LEVEL == "INFO":
            self.LOG_LEVEL = app_config.get("log_level", "INFO")

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get config value from YAML by dot notation (e.g., 'llm.temperature')."""
        try:
            value = YAML_CONFIG
            for part in key.split("."):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def load_yaml_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load YAML config file."""
    if config_path is None:
        return YAML_CONFIG

    config_path = Path(config_path) if not isinstance(config_path, Path) else config_path
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
