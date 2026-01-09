"""Streaming example for UnifyLLM."""

from src import UnifyLLM

# Example 1: Streaming with OpenAI
print("=" * 50)
print("Example 1: Streaming with OpenAI")
print("=" * 50)

client = UnifyLLM(
    provider="openai",
    api_key="your-openai-api-key-here"
)

print("Generating story...\n")

for chunk in client.chat_stream(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Tell me a short story about a robot learning to paint."}
    ],
    max_tokens=500
):
    if chunk.content:
        print(chunk.content, end="", flush=True)

print("\n\n")

# Example 2: Streaming with Anthropic
print("=" * 50)
print("Example 2: Streaming with Anthropic")
print("=" * 50)

client = UnifyLLM(
    provider="anthropic",
    api_key="your-anthropic-api-key-here"
)

print("Generating explanation...\n")

for chunk in client.chat_stream(
    model="claude-3-sonnet-20240229",
    messages=[
        {"role": "user", "content": "Explain how neural networks work."}
    ],
    max_tokens=1000
):
    if chunk.content:
        print(chunk.content, end="", flush=True)

print("\n\n")

# Example 3: Streaming with finish reason detection
print("=" * 50)
print("Example 3: Detecting Stream Completion")
print("=" * 50)

client = UnifyLLM(
    provider="openai",
    api_key="your-openai-api-key-here"
)

full_response = ""
for chunk in client.chat_stream(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "Count from 1 to 10."}
    ],
    max_tokens=100
):
    if chunk.content:
        print(chunk.content, end="", flush=True)
        full_response += chunk.content

    # Check if streaming is complete
    if chunk.finish_reason:
        print(f"\n\n[Stream completed: {chunk.finish_reason}]")
        break

print(f"\nFull response length: {len(full_response)} characters")
print()

# Example 4: Streaming with Ollama
print("=" * 50)
print("Example 4: Streaming with Ollama")
print("=" * 50)

client = UnifyLLM(provider="ollama")

print("Generating response...\n")

for chunk in client.chat_stream(
    model="llama2",
    messages=[
        {"role": "user", "content": "What are the benefits of open source software?"}
    ]
):
    if chunk.content:
        print(chunk.content, end="", flush=True)

print("\n")
