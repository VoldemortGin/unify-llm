"""
Simple tests for new providers and LangChain compatibility

These tests verify that the new providers (Qwen, ByteDance) are properly
integrated and that the LangChain-compatible methods work correctly.
"""

from src import UnifyLLM, LangChainAdapter
from src.providers import QwenProvider, ByteDanceProvider


def test_provider_registration():
    """Test that new providers are registered."""
    print("Testing provider registration...")

    # Check if providers are registered
    assert "qwen" in UnifyLLM._providers
    assert "bytedance" in UnifyLLM._providers
    assert UnifyLLM._providers["qwen"] == QwenProvider
    assert UnifyLLM._providers["bytedance"] == ByteDanceProvider

    print("✓ Providers registered correctly")


def test_client_initialization():
    """Test that clients can be initialized with new providers."""
    print("\nTesting client initialization...")

    # Test Qwen initialization
    try:
        qwen_client = UnifyLLM(provider="qwen", api_key="test-key")
        assert qwen_client._provider.name == "qwen"
        print("✓ Qwen client initialized")
    except Exception as e:
        print(f"✗ Qwen initialization failed: {e}")

    # Test ByteDance initialization
    try:
        bytedance_client = UnifyLLM(provider="bytedance", api_key="test-key")
        assert bytedance_client._provider.name == "bytedance"
        print("✓ ByteDance client initialized")
    except Exception as e:
        print(f"✗ ByteDance initialization failed: {e}")


def test_langchain_methods():
    """Test that LangChain-compatible methods exist."""
    print("\nTesting LangChain-compatible methods...")

    client = UnifyLLM(provider="openai", api_key="test-key")

    # Check that methods exist
    assert hasattr(client, "invoke")
    assert hasattr(client, "ainvoke")
    assert hasattr(client, "stream")
    assert hasattr(client, "astream")

    print("✓ All LangChain methods exist")


def test_langchain_adapter():
    """Test LangChainAdapter initialization and methods."""
    print("\nTesting LangChain adapter...")

    # Test adapter initialization with all providers
    providers = ["openai", "anthropic", "gemini", "ollama", "qwen", "bytedance"]

    for provider in providers:
        try:
            adapter = LangChainAdapter(provider=provider, api_key="test-key")
            assert hasattr(adapter, "invoke")
            assert hasattr(adapter, "ainvoke")
            assert hasattr(adapter, "stream")
            assert hasattr(adapter, "astream")
            assert hasattr(adapter, "set_default_model")
            assert hasattr(adapter, "get_raw_client")
            print(f"✓ {provider} adapter works")
        except Exception as e:
            print(f"✗ {provider} adapter failed: {e}")


def test_default_model():
    """Test default model functionality."""
    print("\nTesting default model...")

    adapter = LangChainAdapter(provider="openai", api_key="test-key")

    # Set default model
    adapter.set_default_model("gpt-4")
    assert adapter._default_model == "gpt-4"

    print("✓ Default model functionality works")


def test_method_signatures():
    """Test that method signatures match expected LangChain format."""
    print("\nTesting method signatures...")

    import inspect

    client = UnifyLLM(provider="openai", api_key="test-key")

    # Check invoke signature
    invoke_sig = inspect.signature(client.invoke)
    assert "messages" in invoke_sig.parameters
    assert "model" in invoke_sig.parameters
    assert "temperature" in invoke_sig.parameters
    assert "max_tokens" in invoke_sig.parameters

    # Check stream signature
    stream_sig = inspect.signature(client.stream)
    assert "messages" in stream_sig.parameters
    assert "model" in stream_sig.parameters

    print("✓ Method signatures correct")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running UnifyLLM Tests")
    print("=" * 60)

    test_provider_registration()
    test_client_initialization()
    test_langchain_methods()
    test_langchain_adapter()
    test_default_model()
    test_method_signatures()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
