# Contributing to UnifyLLM

感谢您对 UnifyLLM 的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告 Bug

如果您发现了 bug，请创建一个 Issue 并包含：

1. 问题的详细描述
2. 重现步骤
3. 期望的行为
4. 实际的行为
5. 环境信息（Python 版本、操作系统等）

### 提出新功能

如果您有新功能的想法，请创建一个 Issue 并描述：

1. 功能的用途和价值
2. 预期的 API 设计
3. 是否愿意自己实现

### 提交 Pull Request

1. Fork 这个仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建一个 Pull Request

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/unify-llm.git
cd unify-llm

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black unify_llm tests
ruff check unify_llm tests

# 类型检查
mypy unify_llm
```

## 代码规范

- 遵循 PEP 8 代码风格
- 使用 Black 进行代码格式化（100 字符行宽）
- 添加类型注解
- 编写文档字符串
- 添加单元测试

## 添加新的提供商

如果您想添加对新 LLM 提供商的支持：

1. 在 `unifyllm/providers/` 下创建新文件，如 `newprovider.py`
2. 继承 `BaseProvider` 类并实现所有抽象方法
3. 在 `unifyllm/providers/__init__.py` 中导出新提供商
4. 在 `unifyllm/client.py` 的 `_providers` 字典中注册
5. 添加测试用例
6. 更新文档

### 提供商实现模板

```python
from unify_llm.providers.base import BaseProvider


class NewProvider(BaseProvider):
    def _get_headers(self):
        # 返回 HTTP 请求头
        pass

    def _get_base_url(self):
        # 返回 API 基础 URL
        pass

    def _convert_request(self, request):
        # 转换统一请求格式到提供商格式
        pass

    def _convert_response(self, response):
        # 转换提供商响应到统一格式
        pass

    def _convert_stream_chunk(self, chunk):
        # 转换流式响应块
        pass

    def _chat_impl(self, request):
        # 实现同步聊天请求
        pass

    async def _achat_impl(self, request):
        # 实现异步聊天请求
        pass

    def _chat_stream_impl(self, request):
        # 实现同步流式请求
        pass

    async def _achat_stream_impl(self, request):
        # 实现异步流式请求
        pass
```

## 许可证

通过贡献，您同意您的贡献将按照 MIT 许可证授权。
