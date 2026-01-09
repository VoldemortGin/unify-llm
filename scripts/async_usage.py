"""Async usage example for UnifyLLM."""

import asyncio
from src import UnifyLLM


async def example1_async_chat():
    """Example 1: Simple async chat."""
    print("=" * 50)
    print("Example 1: Async Chat")
    print("=" * 50)

    client = UnifyLLM(
        provider="openai",
        api_key="your-openai-api-key-here"
    )

    response = await client.achat(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "What is async programming?"}
        ]
    )

    print(f"Response: {response.content}")
    print()


async def example2_async_stream():
    """Example 2: Async streaming."""
    print("=" * 50)
    print("Example 2: Async Streaming")
    print("=" * 50)

    client = UnifyLLM(
        provider="anthropic",
        api_key="your-anthropic-api-key-here"
    )

    print("Generating response...\n")

    async for chunk in client.achat_stream(
        model="claude-3-sonnet-20240229",
        messages=[
            {"role": "user", "content": "Write a poem about async programming."}
        ]
    ):
        if chunk.content:
            print(chunk.content, end="", flush=True)

    print("\n")


async def example3_concurrent_requests():
    """Example 3: Multiple concurrent requests."""
    print("=" * 50)
    print("Example 3: Concurrent Requests")
    print("=" * 50)

    client = UnifyLLM(
        provider="openai",
        api_key="your-openai-api-key-here"
    )

    # Create multiple tasks
    tasks = [
        client.achat(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Tell me a fact about {topic}"}]
        )
        for topic in ["Python", "JavaScript", "Rust", "Go", "TypeScript"]
    ]

    # Run all tasks concurrently
    print("Fetching facts about 5 programming languages concurrently...")
    responses = await asyncio.gather(*tasks)

    # Print results
    for i, response in enumerate(responses):
        topic = ["Python", "JavaScript", "Rust", "Go", "TypeScript"][i]
        print(f"\n{topic}: {response.content}")

    print()


async def example4_multi_provider():
    """Example 4: Using multiple providers concurrently."""
    print("=" * 50)
    print("Example 4: Multi-Provider Concurrent Requests")
    print("=" * 50)

    # Create clients for different providers
    openai_client = UnifyLLM(provider="openai", api_key="your-openai-api-key")
    anthropic_client = UnifyLLM(provider="anthropic", api_key="your-anthropic-api-key")
    gemini_client = UnifyLLM(provider="gemini", api_key="your-gemini-api-key")

    question = "What is the capital of France?"

    # Ask the same question to all providers concurrently
    tasks = [
        openai_client.achat(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": question}]
        ),
        anthropic_client.achat(
            model="claude-3-sonnet-20240229",
            messages=[{"role": "user", "content": question}]
        ),
        gemini_client.achat(
            model="gemini-pro",
            messages=[{"role": "user", "content": question}]
        ),
    ]

    print(f"Question: {question}\n")
    print("Asking multiple providers concurrently...\n")

    responses = await asyncio.gather(*tasks)

    providers = ["OpenAI", "Anthropic", "Gemini"]
    for provider, response in zip(providers, responses):
        print(f"{provider}: {response.content}\n")


async def example5_error_handling():
    """Example 5: Error handling in async context."""
    print("=" * 50)
    print("Example 5: Async Error Handling")
    print("=" * 50)

    client = UnifyLLM(
        provider="openai",
        api_key="invalid-key"  # Intentionally invalid
    )

    try:
        response = await client.achat(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}]
        )
        print(response.content)
    except Exception as e:
        print(f"Caught error: {e.__class__.__name__}")
        print(f"Error message: {e}")

    print()


async def main():
    """Run all examples."""
    await example1_async_chat()
    await example2_async_stream()
    await example3_concurrent_requests()
    await example4_multi_provider()
    await example5_error_handling()


if __name__ == "__main__":
    asyncio.run(main())
