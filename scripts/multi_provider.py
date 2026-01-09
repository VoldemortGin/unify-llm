"""Multi-provider comparison example."""

from src import UnifyLLM


def compare_providers():
    """Compare responses from different providers for the same prompt."""

    # Define the prompt
    prompt = "Explain the concept of recursion in programming in 2-3 sentences."

    # Configure providers
    providers = {
        "OpenAI GPT-4": {
            "provider": "openai",
            "api_key": "your-openai-api-key",
            "model": "gpt-4"
        },
        "OpenAI GPT-3.5": {
            "provider": "openai",
            "api_key": "your-openai-api-key",
            "model": "gpt-3.5-turbo"
        },
        "Anthropic Claude": {
            "provider": "anthropic",
            "api_key": "your-anthropic-api-key",
            "model": "claude-3-sonnet-20240229"
        },
        "Google Gemini": {
            "provider": "gemini",
            "api_key": "your-gemini-api-key",
            "model": "gemini-pro"
        },
        "Ollama Llama2": {
            "provider": "ollama",
            "model": "llama2"
        }
    }

    print("=" * 70)
    print("MULTI-PROVIDER COMPARISON")
    print("=" * 70)
    print(f"\nPrompt: {prompt}\n")
    print("=" * 70)

    results = {}

    for name, config in providers.items():
        print(f"\n{name}:")
        print("-" * 70)

        try:
            # Create client
            if "api_key" in config:
                client = UnifyLLM(
                    provider=config["provider"],
                    api_key=config["api_key"]
                )
            else:
                client = UnifyLLM(provider=config["provider"])

            # Make request
            response = client.chat(
                model=config["model"],
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )

            results[name] = {
                "content": response.content,
                "tokens": response.usage.total_tokens,
                "model": response.model
            }

            print(f"Response: {response.content}")
            print(f"Tokens used: {response.usage.total_tokens}")

        except Exception as e:
            print(f"Error: {e}")
            results[name] = {"error": str(e)}

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for name, result in results.items():
        if "error" not in result:
            print(f"\n{name}:")
            print(f"  - Length: {len(result['content'])} characters")
            print(f"  - Tokens: {result['tokens']}")
            print(f"  - Model: {result['model']}")


def test_streaming_comparison():
    """Compare streaming performance across providers."""

    print("\n\n" + "=" * 70)
    print("STREAMING COMPARISON")
    print("=" * 70)

    prompt = "Write a short paragraph about artificial intelligence."

    providers = [
        ("OpenAI", "openai", "gpt-3.5-turbo", "your-openai-api-key"),
        ("Anthropic", "anthropic", "claude-3-sonnet-20240229", "your-anthropic-api-key"),
        ("Ollama", "ollama", "llama2", None),
    ]

    for name, provider, model, api_key in providers:
        print(f"\n{name} ({model}):")
        print("-" * 70)

        try:
            if api_key:
                client = UnifyLLM(provider=provider, api_key=api_key)
            else:
                client = UnifyLLM(provider=provider)

            chunk_count = 0
            for chunk in client.chat_stream(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            ):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
                    chunk_count += 1

            print(f"\n\n[Received {chunk_count} chunks]")

        except Exception as e:
            print(f"Error: {e}")


def custom_provider_example():
    """Example of registering a custom provider."""

    print("\n\n" + "=" * 70)
    print("CUSTOM PROVIDER EXAMPLE")
    print("=" * 70)

    # Note: You would need to implement CustomProvider inheriting from BaseProvider
    # This is just a placeholder to show the API

    print("""
To register a custom provider:

```python
from src import UnifyLLM
from src.providers import BaseProvider

class MyCustomProvider(BaseProvider):
    # ... implementation ...
    pass

# Register the provider
UnifyLLM.register_provider("custom", MyCustomProvider)

# Use it
client = UnifyLLM(provider="custom", api_key="...")
response = client.chat(
    model="my-model",
    messages=[{"role": "user", "content": "Hello"}]
)
```
    """)


if __name__ == "__main__":
    compare_providers()
    test_streaming_comparison()
    custom_provider_example()
