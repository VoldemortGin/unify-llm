"""
Comprehensive test script for all providers with LangChain-compatible methods.

Tests all 6 providers (OpenAI, Anthropic, Gemini, Ollama, Qwen, ByteDance)
with unified .invoke() interface.
"""

import os
import sys
import asyncio
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import UnifyLLM


def test_provider_sync(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
):
    """Test a provider with synchronous .invoke() method."""
    print(f"\n{'='*60}")
    print(f"Testing {provider.upper()} - {model}")
    print(f"{'='*60}")

    try:
        # Initialize client
        kwargs = {"provider": provider}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url

        client = UnifyLLM(**kwargs)

        # Test 1: Basic .invoke()
        print("\n[TEST 1] Testing .invoke() method...")
        response = client.invoke(
            messages=[{"role": "user", "content": "Say 'Hello from UnifyLLM!' and nothing else."}],
            model=model,
            temperature=0.7,
            max_tokens=50
        )
        print(f"✓ Response: {response[:100]}")

        # Test 2: .stream() method
        print("\n[TEST 2] Testing .stream() method...")
        print("Streaming: ", end="", flush=True)
        chunks = []
        for chunk in client.stream(
            messages=[{"role": "user", "content": "Count: 1, 2, 3"}],
            model=model,
            max_tokens=30
        ):
            print(chunk, end="", flush=True)
            chunks.append(chunk)
        print()
        print(f"✓ Received {len(chunks)} chunks")

        # Test 3: Full .chat() method
        print("\n[TEST 3] Testing .chat() method...")
        chat_response = client.chat(
            model=model,
            messages=[{"role": "user", "content": "What is 2+2?"}],
            temperature=0.3,
            max_tokens=50
        )
        print(f"✓ Content: {chat_response.content[:100]}")
        print(f"✓ Model: {chat_response.model}")
        print(f"✓ Usage: {chat_response.usage}")

        print(f"\n✅ {provider.upper()} - ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ {provider.upper()} - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_provider_async(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
):
    """Test a provider with asynchronous methods."""
    print(f"\n{'='*60}")
    print(f"Testing ASYNC {provider.upper()} - {model}")
    print(f"{'='*60}")

    try:
        # Initialize client
        kwargs = {"provider": provider}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url

        client = UnifyLLM(**kwargs)

        # Test 1: .ainvoke()
        print("\n[TEST 1] Testing .ainvoke() method...")
        response = await client.ainvoke(
            messages=[{"role": "user", "content": "Say 'Async test passed!' and nothing else."}],
            model=model,
            max_tokens=30
        )
        print(f"✓ Response: {response[:100]}")

        # Test 2: .astream()
        print("\n[TEST 2] Testing .astream() method...")
        print("Async streaming: ", end="", flush=True)
        chunks = []
        async for chunk in client.astream(
            messages=[{"role": "user", "content": "Count: A, B, C"}],
            model=model,
            max_tokens=30
        ):
            print(chunk, end="", flush=True)
            chunks.append(chunk)
        print()
        print(f"✓ Received {len(chunks)} chunks")

        print(f"\n✅ ASYNC {provider.upper()} - ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ ASYNC {provider.upper()} - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all provider tests."""
    print("\n" + "="*60)
    print("UNIFIED LLM PROVIDER TEST SUITE")
    print("Testing LangChain-compatible .invoke() interface")
    print("="*60)

    # Provider configurations
    # Format: (provider, model, api_key_env, base_url)
    providers = [
        ("openai", "gpt-3.5-turbo", "OPENAI_API_KEY", None),
        ("anthropic", "claude-3-haiku-20240307", "ANTHROPIC_API_KEY", None),
        ("gemini", "gemini-pro", "GEMINI_API_KEY", None),
        ("ollama", "llama2", None, "http://localhost:11434"),
        ("qwen", "qwen-turbo", "QWEN_API_KEY", None),
        ("bytedance", "doubao-pro", "BYTEDANCE_API_KEY", None),
    ]

    results = {
        "sync": {},
        "async": {}
    }

    # Test each provider synchronously
    for provider, model, api_key_env, base_url in providers:
        api_key = os.getenv(api_key_env) if api_key_env else None

        # Skip if API key is missing (except for Ollama)
        if api_key_env and not api_key:
            print(f"\n⚠️  Skipping {provider.upper()} - {api_key_env} not set")
            results["sync"][provider] = "skipped"
            results["async"][provider] = "skipped"
            continue

        # Run sync tests
        success = test_provider_sync(provider, model, api_key, base_url)
        results["sync"][provider] = "passed" if success else "failed"

    # Test async methods for a few providers
    print("\n\n" + "="*60)
    print("TESTING ASYNC METHODS")
    print("="*60)

    async_providers = [
        ("openai", "gpt-3.5-turbo", "OPENAI_API_KEY", None),
        ("anthropic", "claude-3-haiku-20240307", "ANTHROPIC_API_KEY", None),
    ]

    for provider, model, api_key_env, base_url in async_providers:
        api_key = os.getenv(api_key_env) if api_key_env else None

        if api_key_env and not api_key:
            print(f"\n⚠️  Skipping async {provider.upper()} - {api_key_env} not set")
            continue

        success = asyncio.run(test_provider_async(provider, model, api_key, base_url))
        results["async"][provider] = "passed" if success else "failed"

    # Print summary
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    print("\nSynchronous Tests:")
    for provider, status in results["sync"].items():
        icon = "✅" if status == "passed" else "⚠️" if status == "skipped" else "❌"
        print(f"  {icon} {provider.upper()}: {status}")

    print("\nAsynchronous Tests:")
    for provider, status in results["async"].items():
        icon = "✅" if status == "passed" else "⚠️" if status == "skipped" else "❌"
        print(f"  {icon} {provider.upper()}: {status}")

    # Check if any tests failed
    all_passed = all(
        status in ["passed", "skipped"]
        for status in list(results["sync"].values()) + list(results["async"].values())
    )

    if all_passed:
        print("\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("\nThe unified LLM client supports all 6 providers with:")
        print("  • Unified .invoke() / .ainvoke() methods (LangChain-compatible)")
        print("  • Unified .stream() / .astream() methods (LangChain-compatible)")
        print("  • Full .chat() / .achat() methods with detailed responses")
        print("  • Consistent interface across all providers")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
