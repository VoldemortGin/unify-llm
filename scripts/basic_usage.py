"""Basic usage example for UnifyLLM."""

from unify_llm import UnifyLLM

# Example 1: OpenAI
print("=" * 50)
print("Example 1: OpenAI GPT-4")
print("=" * 50)

client = UnifyLLM(
    provider="openai",
    api_key="your-openai-api-key-here"  # Or set OPENAI_API_KEY env var
)

response = client.chat(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Python?"}
    ],
    temperature=0.7,
    max_tokens=500
)

print(f"Response: {response.content}")
print(f"Model: {response.model}")
print(f"Tokens used: {response.usage.total_tokens}")
print()

# Example 2: Anthropic Claude
print("=" * 50)
print("Example 2: Anthropic Claude")
print("=" * 50)

client = UnifyLLM(
    provider="anthropic",
    api_key="your-anthropic-api-key-here"  # Or set ANTHROPIC_API_KEY env var
)

response = client.chat(
    model="claude-3-sonnet-20240229",
    messages=[
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    max_tokens=1000
)

print(f"Response: {response.content}")
print(f"Finish reason: {response.finish_reason}")
print()

# Example 3: Google Gemini
print("=" * 50)
print("Example 3: Google Gemini")
print("=" * 50)

client = UnifyLLM(
    provider="gemini",
    api_key="your-gemini-api-key-here"  # Or set GEMINI_API_KEY env var
)

response = client.chat(
    model="gemini-pro",
    messages=[
        {"role": "user", "content": "Write a haiku about programming."}
    ],
    temperature=0.9
)

print(f"Response: {response.content}")
print()

# Example 4: Ollama (local model)
print("=" * 50)
print("Example 4: Ollama (Local)")
print("=" * 50)

client = UnifyLLM(
    provider="ollama",
    base_url="http://localhost:11434"  # Default Ollama URL
)

response = client.chat(
    model="llama2",  # Make sure llama2 is pulled: ollama pull llama2
    messages=[
        {"role": "user", "content": "Tell me a fun fact about space."}
    ]
)

print(f"Response: {response.content}")
print()

# Example 5: Using environment variables for API keys
print("=" * 50)
print("Example 5: Using Environment Variables")
print("=" * 50)

# Just provide provider name, API key will be read from env
# Make sure to set OPENAI_API_KEY environment variable
try:
    client = UnifyLLM(provider="openai")

    response = client.chat(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello!"}]
    )

    print(f"Response: {response.content}")
except Exception as e:
    print(f"Error: {e}")
    print("Make sure to set the OPENAI_API_KEY environment variable")
