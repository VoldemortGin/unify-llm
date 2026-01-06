"""
Quick reference for using the unified LLM client.

All 6 providers (OpenAI, Anthropic, Gemini, Ollama, Qwen, ByteDance)
use the exact same interface!
"""

from unify_llm import UnifyLLM
import asyncio


# =============================================================================
# BASIC USAGE - Just change the provider name!
# =============================================================================

def example_all_providers():
    """Show how all providers use the same interface."""

    # Provider configurations: (name, model)
    configs = [
        ("openai", "gpt-4"),
        ("anthropic", "claude-3-sonnet-20240229"),
        ("gemini", "gemini-pro"),
        ("ollama", "llama2"),  # Requires local Ollama server
        ("qwen", "qwen-max"),
        ("bytedance", "doubao-pro"),
    ]

    for provider, model in configs:
        print(f"\n{'='*60}")
        print(f"{provider.upper()} with {model}")
        print('='*60)

        # Same code for all providers!
        client = UnifyLLM(provider=provider)

        # LangChain-compatible .invoke()
        response = client.invoke(
            messages=[{"role": "user", "content": "Say hello!"}],
            model=model,
            temperature=0.7,
            max_tokens=50
        )
        print(f"Response: {response}")


# =============================================================================
# LANGCHAIN-COMPATIBLE METHODS (returns just text)
# =============================================================================

def langchain_style_sync():
    """LangChain-compatible synchronous methods."""
    client = UnifyLLM(provider="openai")

    # 1. invoke() - returns just the text
    response = client.invoke(
        messages=[{"role": "user", "content": "What is 2+2?"}],
        model="gpt-4",
        temperature=0.3
    )
    print(f"invoke() result: {response}")

    # 2. stream() - yields text chunks
    print("\nstream() result: ", end="", flush=True)
    for chunk in client.stream(
        messages=[{"role": "user", "content": "Count to 5"}],
        model="gpt-4"
    ):
        print(chunk, end="", flush=True)
    print()


async def langchain_style_async():
    """LangChain-compatible asynchronous methods."""
    client = UnifyLLM(provider="anthropic")

    # 1. ainvoke() - async version, returns text
    response = await client.ainvoke(
        messages=[{"role": "user", "content": "What is AI?"}],
        model="claude-3-haiku-20240307",
        max_tokens=100
    )
    print(f"ainvoke() result: {response}")

    # 2. astream() - async streaming, yields text chunks
    print("\nastream() result: ", end="", flush=True)
    async for chunk in client.astream(
        messages=[{"role": "user", "content": "Count: A, B, C"}],
        model="claude-3-haiku-20240307"
    ):
        print(chunk, end="", flush=True)
    print()


# =============================================================================
# FULL RESPONSE METHODS (returns ChatResponse with metadata)
# =============================================================================

def full_response_methods():
    """Methods that return full ChatResponse with metadata."""
    client = UnifyLLM(provider="gemini")

    # 1. chat() - returns ChatResponse object
    response = client.chat(
        model="gemini-pro",
        messages=[{"role": "user", "content": "Hello!"}],
        temperature=0.7
    )

    # Access metadata
    print(f"Response ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Content: {response.content}")
    print(f"Finish Reason: {response.finish_reason}")
    print(f"Usage: {response.usage}")
    print(f"  - Prompt tokens: {response.usage.prompt_tokens}")
    print(f"  - Completion tokens: {response.usage.completion_tokens}")
    print(f"  - Total tokens: {response.usage.total_tokens}")


# =============================================================================
# SWITCHING PROVIDERS - SAME CODE!
# =============================================================================

def provider_comparison():
    """Compare responses from different providers using identical code."""

    messages = [{"role": "user", "content": "What is Python?"}]

    providers = [
        ("openai", "gpt-3.5-turbo"),
        ("anthropic", "claude-3-haiku-20240307"),
        ("gemini", "gemini-pro"),
    ]

    for provider, model in providers:
        client = UnifyLLM(provider=provider)

        # Exact same method call for all!
        response = client.invoke(
            messages=messages,
            model=model,
            temperature=0.5,
            max_tokens=100
        )

        print(f"\n[{provider.upper()}]")
        print(response)


# =============================================================================
# INITIALIZATION OPTIONS
# =============================================================================

def initialization_examples():
    """Different ways to initialize the client."""

    # 1. Basic - API key from environment variable
    client1 = UnifyLLM(provider="openai")
    # Looks for OPENAI_API_KEY env var

    # 2. With explicit API key
    client2 = UnifyLLM(
        provider="anthropic",
        api_key="sk-ant-..."
    )

    # 3. With custom base URL (e.g., for Ollama)
    client3 = UnifyLLM(
        provider="ollama",
        base_url="http://localhost:11434"
    )

    # 4. With timeout and retries
    client4 = UnifyLLM(
        provider="qwen",
        api_key="your-key",
        timeout=120.0,
        max_retries=5
    )

    # 5. With extra headers
    client5 = UnifyLLM(
        provider="bytedance",
        api_key="your-key",
        extra_headers={"Custom-Header": "value"}
    )


# =============================================================================
# MESSAGE FORMATS
# =============================================================================

def message_format_examples():
    """Different message formats (all work the same)."""
    client = UnifyLLM(provider="openai")

    # 1. Dict format (most common)
    response1 = client.invoke(
        messages=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello!"}
        ],
        model="gpt-4"
    )

    # 2. Message object format
    from unify_llm import Message

    response2 = client.invoke(
        messages=[
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello!")
        ],
        model="gpt-4"
    )

    # Both work identically!


# =============================================================================
# COMMON PARAMETERS (work for all providers)
# =============================================================================

def parameter_examples():
    """Common parameters that work across all providers."""
    client = UnifyLLM(provider="openai")

    response = client.invoke(
        messages=[{"role": "user", "content": "Hello"}],
        model="gpt-4",

        # Temperature (0.0 - 2.0, lower = more focused)
        temperature=0.7,

        # Max tokens to generate
        max_tokens=1000,

        # Top-p sampling (0.0 - 1.0)
        top_p=0.9,

        # Stop sequences
        stop=["END", "STOP"],

        # Frequency penalty (-2.0 to 2.0)
        frequency_penalty=0.5,

        # Presence penalty (-2.0 to 2.0)
        presence_penalty=0.5,
    )


# =============================================================================
# QUICK START EXAMPLES
# =============================================================================

def quick_start():
    """Simple examples to get started quickly."""

    print("="*60)
    print("QUICK START EXAMPLES")
    print("="*60)

    # Example 1: Simple question
    print("\n1. Simple Question")
    client = UnifyLLM(provider="openai")
    answer = client.invoke(
        messages=[{"role": "user", "content": "What is 2+2?"}],
        model="gpt-4"
    )
    print(f"Answer: {answer}")

    # Example 2: Streaming
    print("\n2. Streaming Response")
    print("Story: ", end="", flush=True)
    for chunk in client.stream(
        messages=[{"role": "user", "content": "Tell a very short story"}],
        model="gpt-4",
        max_tokens=100
    ):
        print(chunk, end="", flush=True)
    print()

    # Example 3: Different provider
    print("\n3. Using Anthropic Claude")
    claude_client = UnifyLLM(provider="anthropic")
    response = claude_client.invoke(
        messages=[{"role": "user", "content": "Explain AI briefly"}],
        model="claude-3-haiku-20240307",
        max_tokens=100
    )
    print(f"Claude says: {response}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("UNIFIED LLM CLIENT - QUICK REFERENCE")
    print("="*60)

    # Run quick start examples
    quick_start()

    # Run LangChain-style examples
    print("\n" + "="*60)
    print("LANGCHAIN-COMPATIBLE SYNC METHODS")
    print("="*60)
    langchain_style_sync()

    # Run async examples
    print("\n" + "="*60)
    print("LANGCHAIN-COMPATIBLE ASYNC METHODS")
    print("="*60)
    asyncio.run(langchain_style_async())

    print("\n" + "="*60)
    print("✅ ALL EXAMPLES COMPLETED!")
    print("="*60)
    print("\nKey Takeaway:")
    print("  All 6 providers use the EXACT SAME interface!")
    print("  Just change the provider name and you're good to go!")
    print("="*60 + "\n")
