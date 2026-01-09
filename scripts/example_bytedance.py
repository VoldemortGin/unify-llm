"""
Example: Using UnifyLLM with ByteDance Doubao (字节豆包)

This example demonstrates how to use the ByteDance provider with UnifyLLM.
"""

import asyncio
from src import UnifyLLM

# Set your ByteDance API key
# Get it from: https://console.volcengine.com/ark
BYTEDANCE_API_KEY = "your-bytedance-api-key-here"


def basic_chat_example():
    """Basic synchronous chat example with ByteDance."""
    print("=== Basic Chat Example ===\n")

    # Initialize client with ByteDance provider
    client = UnifyLLM(provider="bytedance", api_key=BYTEDANCE_API_KEY)

    # Make a simple chat request
    response = client.chat(
        model="doubao-pro",  # or other ByteDance models
        messages=[
            {"role": "system", "content": "你是一个有帮助的AI助手。"},
            {"role": "user", "content": "请介绍一下自然语言处理"}
        ],
        temperature=0.7,
        max_tokens=1000
    )

    print(f"Response: {response.content}\n")
    print(f"Tokens used: {response.usage.total_tokens}")


def langchain_invoke_example():
    """Example using LangChain-compatible invoke method."""
    print("\n=== LangChain Invoke Example ===\n")

    client = UnifyLLM(provider="bytedance", api_key=BYTEDANCE_API_KEY)

    # Use .invoke() method (returns just the text)
    response = client.invoke(
        model="doubao-pro",
        messages=[{"role": "user", "content": "用一句话总结机器学习的定义"}],
        temperature=0.5
    )

    print(f"Response: {response}")


def streaming_example():
    """Streaming chat example with ByteDance."""
    print("\n=== Streaming Example ===\n")

    client = UnifyLLM(provider="bytedance", api_key=BYTEDANCE_API_KEY)

    print("Streaming response: ", end="", flush=True)

    # Use LangChain-compatible .stream() method
    for chunk in client.stream(
        model="doubao-pro",
        messages=[{"role": "user", "content": "讲一个关于人工智能的故事"}]
    ):
        print(chunk, end="", flush=True)

    print("\n")


async def async_example():
    """Asynchronous chat example with ByteDance."""
    print("\n=== Async Example ===\n")

    client = UnifyLLM(provider="bytedance", api_key=BYTEDANCE_API_KEY)

    # Use async invoke
    response = await client.ainvoke(
        model="doubao-pro",
        messages=[{"role": "user", "content": "深度学习和传统机器学习有什么区别?"}],
        max_tokens=800
    )

    print(f"Async response: {response}")


async def async_streaming_example():
    """Asynchronous streaming example with ByteDance."""
    print("\n=== Async Streaming Example ===\n")

    client = UnifyLLM(provider="bytedance", api_key=BYTEDANCE_API_KEY)

    print("Async streaming: ", end="", flush=True)

    async for chunk in client.astream(
        model="doubao-pro",
        messages=[{"role": "user", "content": "给我一些学习Python的建议"}]
    ):
        print(chunk, end="", flush=True)

    print("\n")


if __name__ == "__main__":
    # Run synchronous examples
    basic_chat_example()
    langchain_invoke_example()
    streaming_example()

    # Run async examples
    asyncio.run(async_example())
    asyncio.run(async_streaming_example())
