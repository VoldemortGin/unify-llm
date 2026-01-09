"""
Example: Using UnifyLLM with Qwen (通义千问)

This example demonstrates how to use the Qwen provider with UnifyLLM.
"""

import asyncio
from src import UnifyLLM

# Set your Qwen API key
# Get it from: https://dashscope.console.aliyun.com/
QWEN_API_KEY = "your-qwen-api-key-here"


def basic_chat_example():
    """Basic synchronous chat example with Qwen."""
    print("=== Basic Chat Example ===\n")

    # Initialize client with Qwen provider
    client = UnifyLLM(provider="qwen", api_key=QWEN_API_KEY)

    # Make a simple chat request
    response = client.chat(
        model="qwen-max",  # or qwen-plus, qwen-turbo
        messages=[
            {"role": "system", "content": "你是一个有帮助的助手。"},
            {"role": "user", "content": "什么是Python编程语言?"}
        ],
        temperature=0.7,
        max_tokens=1000
    )

    print(f"Response: {response.content}\n")
    print(f"Tokens used: {response.usage.total_tokens}")


def langchain_invoke_example():
    """Example using LangChain-compatible invoke method."""
    print("\n=== LangChain Invoke Example ===\n")

    client = UnifyLLM(provider="qwen", api_key=QWEN_API_KEY)

    # Use .invoke() method (returns just the text)
    response = client.invoke(
        model="qwen-max",
        messages=[{"role": "user", "content": "给我讲一个笑话"}],
        temperature=0.9
    )

    print(f"Response: {response}")


def streaming_example():
    """Streaming chat example with Qwen."""
    print("\n=== Streaming Example ===\n")

    client = UnifyLLM(provider="qwen", api_key=QWEN_API_KEY)

    print("Streaming response: ", end="", flush=True)

    # Use LangChain-compatible .stream() method
    for chunk in client.stream(
        model="qwen-turbo",
        messages=[{"role": "user", "content": "用简短的语言介绍一下人工智能的发展历史"}]
    ):
        print(chunk, end="", flush=True)

    print("\n")


async def async_example():
    """Asynchronous chat example with Qwen."""
    print("\n=== Async Example ===\n")

    client = UnifyLLM(provider="qwen", api_key=QWEN_API_KEY)

    # Use async invoke
    response = await client.ainvoke(
        model="qwen-max",
        messages=[{"role": "user", "content": "解释一下量子计算的基本原理"}],
        max_tokens=500
    )

    print(f"Async response: {response}")


async def async_streaming_example():
    """Asynchronous streaming example with Qwen."""
    print("\n=== Async Streaming Example ===\n")

    client = UnifyLLM(provider="qwen", api_key=QWEN_API_KEY)

    print("Async streaming: ", end="", flush=True)

    async for chunk in client.astream(
        model="qwen-turbo",
        messages=[{"role": "user", "content": "写一首关于编程的诗"}]
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
