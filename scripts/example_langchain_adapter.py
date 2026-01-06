"""
Example: Using LangChain Adapter with Multiple Providers

This example demonstrates using the LangChainAdapter for seamless
LangChain-compatible usage across different providers.
"""

import asyncio
from unify_llm import LangChainAdapter


def compare_providers():
    """Compare responses from different providers using the same interface."""
    print("=== Comparing Providers ===\n")

    providers_config = [
        ("openai", "gpt-4"),
        ("anthropic", "claude-3-sonnet-20240229"),
        ("gemini", "gemini-pro"),
        ("qwen", "qwen-max"),
        ("bytedance", "doubao-pro"),
    ]

    question = "What is artificial intelligence in one sentence?"

    for provider_name, model in providers_config:
        print(f"\n[{provider_name.upper()}] Using model: {model}")
        try:
            # Create adapter for each provider
            llm = LangChainAdapter(provider=provider_name)

            # Use unified .invoke() interface
            response = llm.invoke(
                messages=[{"role": "user", "content": question}],
                model=model,
                temperature=0.7,
                max_tokens=100
            )

            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")


def streaming_with_adapter():
    """Streaming example using LangChainAdapter."""
    print("\n\n=== Streaming with Adapter ===\n")

    # Create adapter with default model
    llm = LangChainAdapter(provider="openai")
    llm.set_default_model("gpt-4")

    print("Streaming response: ", end="", flush=True)

    # Now we can omit the model parameter
    for chunk in llm.stream(
        messages=[{"role": "user", "content": "Write a haiku about coding"}]
    ):
        print(chunk, end="", flush=True)

    print("\n")


async def async_adapter_example():
    """Async example with LangChainAdapter."""
    print("\n=== Async Adapter Example ===\n")

    llm = LangChainAdapter(provider="anthropic")

    response = await llm.ainvoke(
        messages=[{"role": "user", "content": "Explain LangChain in simple terms"}],
        model="claude-3-sonnet-20240229",
        max_tokens=200
    )

    print(f"Response: {response}")


def access_raw_client():
    """Example showing how to access the raw UnifyLLM client."""
    print("\n=== Accessing Raw Client ===\n")

    llm = LangChainAdapter(provider="gemini")

    # Get the raw client for full ChatResponse
    raw_client = llm.get_raw_client()

    response = raw_client.chat(
        model="gemini-pro",
        messages=[{"role": "user", "content": "Hello!"}],
        temperature=0.7
    )

    # Access full response metadata
    print(f"Response ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Content: {response.content}")
    print(f"Finish Reason: {response.finish_reason}")
    print(f"Usage: {response.usage}")


async def multi_provider_async_streaming():
    """Stream from multiple providers concurrently."""
    print("\n=== Multi-Provider Async Streaming ===\n")

    providers = [
        ("openai", "gpt-3.5-turbo"),
        ("anthropic", "claude-3-haiku-20240307"),
    ]

    async def stream_from_provider(provider_name, model):
        print(f"\n[{provider_name.upper()}]")
        llm = LangChainAdapter(provider=provider_name)

        async for chunk in llm.astream(
            messages=[{"role": "user", "content": "Count to 5"}],
            model=model,
            max_tokens=50
        ):
            print(f"[{provider_name}] {chunk}", end="", flush=True)
        print()

    # Run streams concurrently
    await asyncio.gather(*[
        stream_from_provider(provider, model)
        for provider, model in providers
    ])


if __name__ == "__main__":
    # Run synchronous examples
    compare_providers()
    streaming_with_adapter()
    access_raw_client()

    # Run async examples
    asyncio.run(async_adapter_example())
    asyncio.run(multi_provider_async_streaming())
