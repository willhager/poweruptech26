from agent2.utils import system_prompt

import anthropic

# Set your API key as an environment variable: ANTHROPIC_API_KEY
# or pass it directly: anthropic.Anthropic(api_key="your-key-here")
client = anthropic.Anthropic()

def call_claude(prompt: str, model: str = "claude-sonnet-5", max_tokens: int = 1024) -> str:
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "user", "content": system_prompt + prompt}
        ]
    )
    return message.content[0].text

