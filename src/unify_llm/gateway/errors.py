"""OpenAI 风格错误信封映射 + FastAPI 异常处理器(ADR-09)。

把内部统一异常树归一为 ``{"error": {"message", "type", "code"}}`` 信封。安全第一:上游错误
(ProviderError/APIError/传输层错)与未知异常一律返回**通用消息**,绝不回显异常原文——上游错误
可能在 URL/消息里夹带密钥(如 Gemini 的 ``?key=``),回显即泄露。
"""

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from unify_llm.core.exceptions import (
    APIError,
    AuthenticationError,
    ContentFilterError,
    InvalidRequestError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
    UnifyLLMError,
)
from unify_llm.core.exceptions import TimeoutError as UnifyTimeoutError


class ModelNotAllowedError(UnifyLLMError):
    """请求的 model 不在该应用的允许列表内(网关级鉴权错,403)。"""

    def __init__(
        self,
        message: str = "Model not allowed for this application",
        provider: str | None = None,
        response: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, provider, status_code=403, response=response)


def _body(message: str, error_type: str, code: str | None) -> dict[str, object]:
    """构造 OpenAI 风格 error 信封体。"""
    return {"error": {"message": message, "type": error_type, "code": code}}


def to_envelope(exc: Exception) -> tuple[int, dict[str, object], dict[str, str]]:
    """异常 → (status_code, OpenAI 信封体, 额外响应头)。最具体的分支在前。

    回显策略:鉴权/限流/请求校验类错误(消息由网关或上游错误体生成,不含本端密钥)回显其消息;
    上游错与未知错(可能夹带密钥/栈)一律通用消息。
    """
    headers: dict[str, str] = {}

    if isinstance(exc, ModelNotAllowedError):
        return 403, _body(exc.message, "invalid_request_error", "model_not_allowed"), headers
    if isinstance(exc, AuthenticationError):
        return 401, _body(exc.message, "authentication_error", None), headers
    if isinstance(exc, RateLimitError):
        if exc.retry_after is not None:
            headers["Retry-After"] = str(int(exc.retry_after))
        return 429, _body(exc.message, "rate_limit_error", None), headers
    if isinstance(exc, UnifyTimeoutError):
        return 504, _body(exc.message, "timeout_error", None), headers
    if isinstance(exc, ModelNotFoundError):
        # ModelNotFoundError 是 InvalidRequestError 子类,必须先判。
        return 404, _body(exc.message, "invalid_request_error", "model_not_found"), headers
    if isinstance(exc, ContentFilterError):
        return 400, _body(exc.message, "content_filter", None), headers
    if isinstance(exc, InvalidRequestError):
        return 400, _body(exc.message, "invalid_request_error", None), headers
    if isinstance(exc, ProviderError | APIError):
        # 上游错:通用消息,绝不回显原文(可能含 URL 里的上游密钥)。
        return 502, _body("Upstream provider error", "upstream_error", None), headers
    if isinstance(exc, httpx.RequestError):
        return 502, _body("Upstream request failed", "upstream_error", None), headers
    if isinstance(exc, UnifyLLMError):
        return 500, _body("Internal server error", "internal_error", None), headers
    # 任何其他异常:通用 500,绝不回显异常文本(防泄密钥/上游 key/栈)。
    return 500, _body("Internal server error", "internal_error", None), headers


def register_exception_handlers(app: FastAPI) -> None:
    """注册统一异常 → 信封处理器。

    ``UnifyLLMError`` / ``httpx.RequestError`` 走 Starlette 的 ExceptionMiddleware(返回信封,不再
    抛出);裸 ``Exception`` 作为生产安全网(ServerErrorMiddleware)兜底为通用 500 信封。
    """

    async def _envelope_handler(request: Request, exc: Exception) -> JSONResponse:
        status_code, body, headers = to_envelope(exc)
        return JSONResponse(status_code=status_code, content=body, headers=headers)

    app.add_exception_handler(UnifyLLMError, _envelope_handler)
    app.add_exception_handler(httpx.RequestError, _envelope_handler)
    app.add_exception_handler(Exception, _envelope_handler)
