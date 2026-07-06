"""Shared Anthropic client used by all three agents.

Two credit-saving techniques live here:

1. Prompt caching: the large, static system prompt (instructions and, for the
   matching agent, the candidate company list) is sent in a cached ``system``
   block. Repeat calls within the cache window are billed at a large discount
   on those tokens, and only the small per-email payload is charged at full
   price.
2. Mock mode: when ``MOCK_CLAUDE`` is set, no network call is made at all so
   the full pipeline can be exercised for free.
"""

import json

from config import MOCK_CLAUDE

_client = None


def _get_client():
    global _client
    if _client is None:
        # Imported lazily so mock/dry-run mode works without the SDK installed.
        import anthropic

        # Reads ANTHROPIC_API_KEY from the environment.
        _client = anthropic.Anthropic()
    return _client


def call_claude(system_prompt, user_content, model, max_tokens, mock_response=None):
    """Call Claude with a cached system prompt and a per-request user message.

    In mock mode the ``mock_response`` string is returned verbatim instead of
    hitting the API.
    """
    if MOCK_CLAUDE:
        return mock_response if mock_response is not None else "{}"

    client = _get_client()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )
    return message.content[0].text


def extract_json(text):
    """Best-effort parse of a JSON value from a model response.

    Handles clean JSON, ```json fenced blocks, and stray text around the JSON.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty response from model")

    if text.startswith("```"):
        inner = text[3:]
        if inner.lower().startswith("json"):
            inner = inner[4:]
        if inner.endswith("```"):
            inner = inner[:-3]
        text = inner.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fall back to slicing from the first opening bracket to the last
        # closing bracket, which discards any prose the model added.
        candidates = [i for i in (text.find("{"), text.find("[")) if i != -1]
        start = min(candidates) if candidates else -1
        end = max(text.rfind("}"), text.rfind("]"))
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise
