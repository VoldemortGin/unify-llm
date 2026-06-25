"""全局配置的唯一来源:环境变量(APP_*) + .env + configs/settings.yaml。

beartype 叶子约束:本模块不得 import 任何本项目内、希望被检查的模块;只依赖标准库 +
pydantic / pydantic-settings。settings 实例在本模块构建,是 __init__ 在安装 beartype
hook 前唯一允许导入的一方(本身不被检查)。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


def _find_project_root() -> Path:
    """向上找 pyproject.toml 作为项目根;找不到则退回 CWD(部署应以 APP_* 显式指定路径)。"""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return Path.cwd()


_ROOT = _find_project_root()


class RetrieverConfig(BaseModel):
    top_k: int = 5
    rerank_model: str = "cohere/rerank-v4.0-fast"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",  # APP_IS_DEBUG / APP_BEARTYPE_ON ...
        env_nested_delimiter="__",  # APP_RETRIEVER__TOP_K 覆盖嵌套字段
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file=_ROOT / "configs" / "settings.yaml",
        extra="ignore",
    )

    app_env: str = "dev"
    is_debug: bool = False
    beartype_on: bool = True  # 运行时类型检查总开关;仅生产设 APP_BEARTYPE_ON=false

    # provider 选择(唯一装配缝按 env 切换;默认 mock,离线/CI 可跑)
    llm_provider: str = "mock"
    embedder_provider: str = "mock"

    # 运行期可写目录(默认锚定项目根;部署可用 APP_*_DIR 覆盖)
    data_dir: Path = _ROOT / "data"
    log_dir: Path = _ROOT / "logs"

    retriever: RetrieverConfig = RetrieverConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # 优先级从高到低:构造参数 > 环境变量 > .env > yaml > secrets
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> "Settings":
    """缓存的配置访问器(无重复构建)。"""
    return Settings()


# 模块级实例:__init__ 安装 beartype hook 前需读 settings.beartype_on,故在此构建一次。
settings = get_settings()
