#!/usr/bin/env python3
"""测试Databricks client连接"""

import os

import rootutils

ROOT_DIR = rootutils.setup_root(os.getcwd(), indicator=".project-root", pythonpath=True)

from src.client import UnifyLLM
from src.core.config import settings


def main():
    print("=" * 50)
    print("Databricks Client 测试")
    print("=" * 50)

    # 显示配置
    print(f"\nDATABRICKS_BASE_URL: {settings.DATABRICKS_BASE_URL}")
    print(f"DATABRICKS_MODEL: {settings.DATABRICKS_MODEL}")
    print(f"DATABRICKS_API_KEY: {'*' * 10}..." if settings.DATABRICKS_API_KEY else "未设置")

    # 创建client
    client = UnifyLLM(
        provider="databricks",
        api_key=settings.DATABRICKS_API_KEY,
        base_url=settings.DATABRICKS_BASE_URL,
    )

    print("\n✓ Client创建成功")

    # 测试简单对话
    print("\n发送测试消息...")
    try:
        response = client.chat(
            model=settings.DATABRICKS_MODEL,
            messages=[{"role": "user", "content": "你好，请用一句话介绍你自己。"}],
            max_tokens=100,
        )

        print("\n✓ 响应成功!")
        print(f"模型: {response.model}")
        print(f"内容: {response.choices[0].message.content}")
        print(f"Token使用: {response.usage}")

    except Exception as e:
        print(f"\n✗ 请求失败: {e}")


if __name__ == "__main__":
    main()
