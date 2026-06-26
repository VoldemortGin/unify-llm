# unify-llm 网关镜像 — uv 多阶段构建(builder 装依赖 → runtime 非 root 跑 ASGI)。
#
# 只装运行时依赖(不含 dev group),含 fastapi/uvicorn + 可选 redis extra(水平扩容用)。
# 入口是隐藏 key 的 OpenAI 兼容代理网关;上游真实厂商 key 由工厂在请求期从 env 取,绝不进镜像。

# ── builder:用 uv 在 /app/.venv 里把运行时依赖 + 项目装好(editable,.pth 指向 /app/src)──
FROM python:3.13-slim AS builder

# 钉版的 uv 官方静态二进制(无需 pip 装,跨阶段可丢弃)。
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# 字节码预编译加速冷启动;link-mode=copy 让 .venv 自包含(跨 stage 拷贝不依赖 uv 缓存);
# 不在镜像内下载解释器(用基础镜像自带的 CPython 3.13)。
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# 先只拷依赖清单 → 锁定依赖层缓存(改源码不必重装依赖)。README.md 是 pyproject 的 readme,
# 构建 wheel 时需要。
COPY pyproject.toml uv.lock README.md ./

# 第一步:只装运行时依赖(--no-dev 不装 dev group;--extra redis 开水平扩容用的 Redis 后端;
# --no-install-project 此步先不装本项目,纯做依赖层)。
RUN uv sync --frozen --no-dev --no-install-project --extra redis

# 第二步:拷源码后把项目本身装进 .venv(默认 editable,.pth 记录绝对路径 /app/src)。
COPY src ./src
RUN uv sync --frozen --no-dev --extra redis


# ── runtime:非 root、只带 .venv + src + 网关配置样例,curl 探活,uvicorn 跑 ASGI ──
FROM python:3.13-slim AS runtime

# HEALTHCHECK 探活要用 curl;装完即清 apt 缓存。
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 非 root 运行(最小权限);系统账户、无登录、家目录就是 /app。
RUN groupadd --system app \
    && useradd --system --gid app --no-create-home --home-dir /app app

WORKDIR /app

# 只拷运行所需:虚拟环境 + 源码 + 默认网关配置(生产应以挂载/env 覆盖)。
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src ./src
COPY --chown=app:app configs/gateway.yaml ./configs/gateway.yaml

# .venv 上 PATH(无需手动 activate);production → 缺上游 key 硬失败;默认配置源指向镜像内样例。
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    APP_GATEWAY_CONFIG=/app/configs/gateway.yaml

USER app

EXPOSE 8080

# 探活打无鉴权的 /healthz(应 200);失败计入容器健康状态。
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8080/healthz || exit 1

# 模块级 app 由 env/yaml 装配(见 gateway/app.py:_build_default_app);多 worker 共享态走 Redis。
CMD ["uvicorn", "unify_llm.gateway.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
