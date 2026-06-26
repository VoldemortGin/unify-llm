"""Phase 2 转换核心:验证现代化后行为不变。

覆盖 models(StrEnum 向后兼容)、providers.openai(parse-don't-validate 的
_convert_response / _convert_stream_chunk、_convert_request 序列化)、providers.base
(_handle_http_error 错误分类)、utils(搬迁后 YAML 路径仍指向仓库根 configs/)。
不连真网络。
"""

import json

import httpx
import pytest

from unify_llm.adapters.openai_compatible import OpenAIProvider
from unify_llm.core.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    RateLimitError,
)
from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    FinishReason,
    Message,
    ProviderConfig,
    Role,
)
from unify_llm.utils import get_model_name_mapping_path, resolve_model_name


def _provider() -> OpenAIProvider:
    return OpenAIProvider(ProviderConfig(api_key="test-key"))


def _status_error(
    status_code: int, body: dict[str, object], retry_after: str | None = None
) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    headers = {"retry-after": retry_after} if retry_after is not None else {}
    response = httpx.Response(status_code, json=body, headers=headers, request=request)
    return httpx.HTTPStatusError(f"{status_code}", request=request, response=response)


# ── models:StrEnum 向后兼容 ──────────────────────────────────────────────


def test_role_strenum_is_str_and_accepts_plain_string() -> None:
    msg = Message(role="assistant", content="hi")
    assert msg.role is Role.ASSISTANT
    assert msg.role == "assistant"
    assert isinstance(msg.role, str)


def test_finish_reason_strenum_coerced_from_string() -> None:
    response = ChatResponse(
        id="r",
        model="m",
        choices=[],
        created=0,
        provider="openai",
    )
    assert response.finish_reason is None


def test_content_validation_matches_legacy_semantics() -> None:
    # content 省略时不校验(等价旧 field_validator 的 validate_default=False)
    assert Message(role="assistant", tool_calls=[{"id": "1"}]).content is None
    assert Message(role="user").content is None
    # tool 角色显式空 content 允许
    assert Message(role="tool", content=None).content is None
    # 其余角色显式提供空/None content 报错(校验器以 Role 比较,StrEnum 等于字面值)
    with pytest.raises(ValueError, match="Content is required"):
        Message(role="user", content="")
    with pytest.raises(ValueError, match="Content is required"):
        Message(role="assistant", content="")


# ── openai._convert_response:parse-don't-validate ────────────────────────


def test_convert_response_maps_raw_dict() -> None:
    raw: dict[str, object] = {
        "id": "chatcmpl-1",
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hello"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
        "created": 1_700_000_000,
        "object": "chat.completion",  # 额外字段被忽略,不报错
    }
    resp = _provider()._convert_response(raw)
    assert isinstance(resp, ChatResponse)
    assert resp.id == "chatcmpl-1"
    assert resp.model == "gpt-4o"
    assert resp.provider == "openai"
    assert resp.content == "hello"
    assert resp.choices[0].message.role is Role.ASSISTANT
    assert resp.choices[0].finish_reason is FinishReason.STOP
    assert resp.usage is not None
    assert resp.usage.total_tokens == 8
    assert resp.created == 1_700_000_000
    assert resp.raw_response == raw  # 原始响应被保留下来


def test_convert_response_defaults_when_fields_missing() -> None:
    resp = _provider()._convert_response({})
    assert resp.id == ""
    assert resp.model == ""
    assert resp.choices == []
    assert resp.usage is not None
    assert resp.usage.total_tokens == 0
    assert resp.created > 0  # created 缺省回退到当前时间


# ── openai._convert_stream_chunk:parse-don't-validate ────────────────────


def test_convert_stream_chunk_maps_delta() -> None:
    chunk = _provider()._convert_stream_chunk(
        {
            "id": "c1",
            "model": "gpt-4o",
            "choices": [{"index": 0, "delta": {"content": "hi"}}],
        }
    )
    assert chunk is not None
    assert chunk.content == "hi"
    assert chunk.id == "c1"


def test_convert_stream_chunk_returns_none_when_empty() -> None:
    assert _provider()._convert_stream_chunk({}) is None
    assert _provider()._convert_stream_chunk({"choices": []}) is None


# ── openai._convert_request:StrEnum 序列化为字面值 ───────────────────────


def test_convert_request_serializes_role_as_plain_string() -> None:
    req = ChatRequest(model="gpt-4o", messages=[Message(role="user", content="hi")])
    payload = _provider()._convert_request(req)
    assert payload["model"] == "gpt-4o"
    # StrEnum 经 json.dumps 序列化为底层字符串值(httpx 同路径)
    dumped = json.dumps(payload)
    assert '"role": "user"' in dumped


# ── base._handle_http_error:错误分类 ─────────────────────────────────────


def test_handle_http_error_classification() -> None:
    provider = _provider()
    with pytest.raises(AuthenticationError):
        provider._handle_http_error(_status_error(401, {"error": "bad key"}))
    with pytest.raises(InvalidRequestError):
        provider._handle_http_error(_status_error(400, {"error": "bad request"}))


def test_handle_http_error_rate_limit_retry_after() -> None:
    with pytest.raises(RateLimitError) as exc_info:
        _provider()._handle_http_error(_status_error(429, {"error": "slow down"}, retry_after="7"))
    assert exc_info.value.retry_after == 7


# ── utils:src 搬迁后 YAML 路径仍指向仓库根 configs/ ──────────────────────


def test_model_name_mapping_path_resolves_to_repo_configs() -> None:
    path = get_model_name_mapping_path()
    assert path.name == "model_name_mapping.yaml"
    assert path.parent.name == "configs"
    assert path.exists()  # 关键:不再指向不存在的 src/configs


def test_resolve_model_name_reads_repo_yaml() -> None:
    # 真配置里存在的别名,证明路径解析到了实际的根级 YAML
    assert resolve_model_name("openrouter", "claude-4.5") == "anthropic/claude-sonnet-4.5"
    # 非 openrouter 不做映射
    assert resolve_model_name("openai", "gpt-4o") == "gpt-4o"
