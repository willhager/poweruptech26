"""Shared LLM client used by all three agents.

The provider is selected with the ``LLM_PROVIDER`` env var:

* ``gemini`` (default) — Google Gemini. Its generous free tier makes it ideal
  for testing the pipeline end-to-end without spending anything.
* ``claude`` — Anthropic Claude. Flip ``LLM_PROVIDER=claude`` once the wiring
  is verified to run the exact same pipeline on Claude.

Two cost-saving techniques live here:

1. Prompt caching (Claude only): the large, static system prompt (instructions
   and, for the matching agent, the candidate company list) is sent in a cached
   ``system`` block. Repeat calls within the cache window are billed at a large
   discount on those tokens. Gemini applies implicit caching automatically for
   supported models, so no special handling is needed there.
2. Mock mode: when ``MOCK_LLM`` is set, no network call is made at all so the
   full pipeline can be exercised for free and without any SDK installed.
"""

import json
import os

from config import LLM_PROVIDER, MOCK_LLM

_client = None


def _get_gemini_client():
    global _client
    if _client is None:
        # Imported lazily so mock/dry-run mode works without the SDK installed.
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        # If no key is passed, the SDK falls back to GEMINI_API_KEY itself.
        _client = genai.Client(api_key=api_key) if api_key else genai.Client()
    return _client


def _get_claude_client():
    global _client
    if _client is None:
        # Imported lazily so mock/dry-run mode works without the SDK installed.
        import anthropic

        # Reads ANTHROPIC_API_KEY from the environment.
        _client = anthropic.Anthropic()
    return _client


def _call_gemini(system_prompt, user_content, model, max_tokens):
    from google.genai import types

    client = _get_gemini_client()
    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
        ),
    )
    return response.text


def _call_claude(system_prompt, user_content, model, max_tokens):
    client = _get_claude_client()
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


def call_llm(system_prompt, user_content, model, max_tokens, mock_response=None):
    """Call the configured LLM with a system prompt and a per-request user message.

    In mock mode the ``mock_response`` string is returned verbatim instead of
    hitting the API.
    """
    if MOCK_LLM:
        return mock_response if mock_response is not None else "{}"

    if LLM_PROVIDER == "claude":
        return _call_claude(system_prompt, user_content, model, max_tokens)
    if LLM_PROVIDER == "gemini":
        return _call_gemini(system_prompt, user_content, model, max_tokens)
    raise ValueError(
        f"Unknown LLM_PROVIDER {LLM_PROVIDER!r}; expected 'gemini' or 'claude'."
    )


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
