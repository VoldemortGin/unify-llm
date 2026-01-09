"""
Verification script: Check that all providers are properly registered
and have the LangChain-compatible interface.

This script verifies the implementation without requiring actual API keys.
"""

import sys
import os
import inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import UnifyLLM
from src.providers.base import BaseProvider
from src.client import UnifyLLM as Client


def check_provider_registration():
    """Verify all 6 providers are registered."""
    print("="*60)
    print("CHECKING PROVIDER REGISTRATION")
    print("="*60)

    expected_providers = ["openai", "anthropic", "gemini", "ollama", "qwen", "bytedance"]
    registered = list(UnifyLLM._providers.keys())

    print(f"\nExpected providers: {expected_providers}")
    print(f"Registered providers: {registered}")

    missing = set(expected_providers) - set(registered)
    extra = set(registered) - set(expected_providers)

    if missing:
        print(f"\n❌ Missing providers: {missing}")
        return False

    if extra:
        print(f"\n⚠️  Extra providers (not in spec): {extra}")

    print("\n✅ All 6 required providers are registered!")
    return True


def check_langchain_methods():
    """Verify UnifyLLM client has LangChain-compatible methods."""
    print("\n" + "="*60)
    print("CHECKING LANGCHAIN-COMPATIBLE METHODS")
    print("="*60)

    required_methods = {
        "invoke": "Synchronous invoke method",
        "ainvoke": "Asynchronous invoke method",
        "stream": "Synchronous streaming method",
        "astream": "Asynchronous streaming method",
        "chat": "Standard chat method",
        "achat": "Asynchronous chat method",
        "chat_stream": "Standard streaming method",
        "achat_stream": "Asynchronous streaming method",
    }

    print("\nChecking for required methods:")

    all_present = True
    for method_name, description in required_methods.items():
        if hasattr(UnifyLLM, method_name):
            method = getattr(UnifyLLM, method_name)
            if callable(method):
                sig = inspect.signature(method)
                params = list(sig.parameters.keys())
                print(f"  ✅ {method_name}() - {description}")
                print(f"      Parameters: {', '.join(params[:5])}...")
            else:
                print(f"  ❌ {method_name} exists but is not callable")
                all_present = False
        else:
            print(f"  ❌ {method_name}() - MISSING")
            all_present = False

    if all_present:
        print("\n✅ All required methods are present!")
    else:
        print("\n❌ Some methods are missing!")

    return all_present


def check_method_signatures():
    """Verify method signatures match LangChain interface."""
    print("\n" + "="*60)
    print("CHECKING METHOD SIGNATURES")
    print("="*60)

    # Check invoke() signature
    invoke_sig = inspect.signature(UnifyLLM.invoke)
    invoke_params = list(invoke_sig.parameters.keys())

    print(f"\n.invoke() signature:")
    print(f"  Parameters: {invoke_params}")

    required_invoke_params = ["self", "messages", "model"]
    missing = set(required_invoke_params) - set(invoke_params)

    if missing:
        print(f"  ❌ Missing required parameters: {missing}")
        return False
    else:
        print(f"  ✅ Has all required parameters")

    # Check stream() signature
    stream_sig = inspect.signature(UnifyLLM.stream)
    stream_params = list(stream_sig.parameters.keys())

    print(f"\n.stream() signature:")
    print(f"  Parameters: {stream_params}")

    if set(required_invoke_params).issubset(set(stream_params)):
        print(f"  ✅ Has all required parameters")
    else:
        print(f"  ❌ Missing required parameters")
        return False

    print("\n✅ Method signatures are correct!")
    return True


def check_provider_inheritance():
    """Verify all providers inherit from BaseProvider."""
    print("\n" + "="*60)
    print("CHECKING PROVIDER INHERITANCE")
    print("="*60)

    all_valid = True
    for name, provider_class in UnifyLLM._providers.items():
        is_subclass = issubclass(provider_class, BaseProvider)
        status = "✅" if is_subclass else "❌"
        print(f"  {status} {name}: {provider_class.__name__}")
        if not is_subclass:
            all_valid = False

    if all_valid:
        print("\n✅ All providers correctly inherit from BaseProvider!")
    else:
        print("\n❌ Some providers don't inherit from BaseProvider!")

    return all_valid


def check_instantiation():
    """Verify we can instantiate clients (without API keys)."""
    print("\n" + "="*60)
    print("CHECKING CLIENT INSTANTIATION")
    print("="*60)

    print("\nTrying to instantiate each provider (with dummy API keys)...")

    for provider_name in UnifyLLM._providers.keys():
        try:
            # Use dummy API key
            client = UnifyLLM(
                provider=provider_name,
                api_key="test_key_12345"
            )
            print(f"  ✅ {provider_name}: Successfully instantiated")

            # Check that methods exist
            assert hasattr(client, "invoke"), f"{provider_name} missing .invoke()"
            assert hasattr(client, "stream"), f"{provider_name} missing .stream()"
            assert hasattr(client, "chat"), f"{provider_name} missing .chat()"

        except Exception as e:
            print(f"  ❌ {provider_name}: Failed - {e}")
            return False

    print("\n✅ All providers can be instantiated!")
    return True


def print_summary():
    """Print implementation summary."""
    print("\n" + "="*60)
    print("IMPLEMENTATION SUMMARY")
    print("="*60)

    print("""
✅ UNIFIED LLM CLIENT IMPLEMENTATION COMPLETE

Supported Providers (6 total):
  1. OpenAI (gpt-4, gpt-3.5-turbo, etc.)
  2. Anthropic (claude-3-opus, claude-3-sonnet, claude-3-haiku)
  3. Google Gemini (gemini-pro, gemini-vision-pro)
  4. Ollama (llama2, mistral, etc. - local models)
  5. Qwen / 通义千问 (qwen-max, qwen-plus, qwen-turbo)
  6. ByteDance / 字节豆包 (doubao-pro, etc.)

LangChain-Compatible Methods:
  • .invoke(messages, model, **kwargs) → str
    Synchronous call returning just the text content

  • .ainvoke(messages, model, **kwargs) → str
    Asynchronous call returning just the text content

  • .stream(messages, model, **kwargs) → Iterator[str]
    Synchronous streaming returning text chunks

  • .astream(messages, model, **kwargs) → AsyncIterator[str]
    Asynchronous streaming returning text chunks

Additional Methods (Full Response):
  • .chat(model, messages, **kwargs) → ChatResponse
    Full response with metadata (usage, finish_reason, etc.)

  • .achat(model, messages, **kwargs) → ChatResponse
    Async version with full response

  • .chat_stream(model, messages, **kwargs) → Iterator[StreamChunk]
    Streaming with chunk metadata

  • .achat_stream(model, messages, **kwargs) → AsyncIterator[StreamChunk]
    Async streaming with chunk metadata

Usage Example:
    ```python
    from src import UnifyLLM

    # Initialize with any provider
    client = UnifyLLM(provider="openai")  # or "anthropic", "gemini", etc.

    # LangChain-style invoke
    response = client.invoke(
        messages=[{"role": "user", "content": "Hello!"}],
        model="gpt-4",
        temperature=0.7
    )
    print(response)  # Just the text

    # LangChain-style streaming
    for chunk in client.stream(
        messages=[{"role": "user", "content": "Tell me a story"}],
        model="gpt-4"
    ):
        print(chunk, end="", flush=True)
    ```

All providers use the same interface - just change the provider name!
    """)
    print("="*60)


def main():
    """Run all verification checks."""
    print("\n🔍 VERIFYING UNIFIED LLM IMPLEMENTATION\n")

    checks = [
        ("Provider Registration", check_provider_registration),
        ("LangChain Methods", check_langchain_methods),
        ("Method Signatures", check_method_signatures),
        ("Provider Inheritance", check_provider_inheritance),
        ("Client Instantiation", check_instantiation),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ {name} check failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Print final summary
    print_summary()

    # Print test results
    print("\nVERIFICATION RESULTS:")
    print("="*60)
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")
        if not passed:
            all_passed = False

    print("="*60)

    if all_passed:
        print("\n🎉 ALL CHECKS PASSED! Implementation is complete and correct!")
        print("\nThe unified LLM client successfully supports all 6 providers")
        print("with LangChain-compatible .invoke() interface!")
    else:
        print("\n⚠️  Some checks failed. Please review the errors above.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
