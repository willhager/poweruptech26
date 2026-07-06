"""Agent 2: match a startup profile against candidate companies with reasoning."""

import json

from config import SMART_MODEL, AGENT2_MAX_TOKENS, PROMPTS_DIR
from ..claude_client import call_claude, extract_json

PROMPT_FILE = PROMPTS_DIR / "match.txt"

# Canned matches for MOCK_CLAUDE mode (references real companies from
# companies.json so downstream enrichment works).
_MOCK_MATCHES = json.dumps(
    {
        "matches": [
            {
                "name": "Northbridge Analytics",
                "url": "northbridge.io",
                "reasoning": "As an enterprise data analytics consulting firm, Northbridge has clients who need faster operational reporting, which is exactly what Acme Insight's automated dashboards deliver.",
                "match_strength": "88",
            },
            {
                "name": "Harborline Logistics",
                "url": "harborline.com",
                "reasoning": "Harborline runs global freight and warehousing operations that generate large volumes of operational data, a strong fit for Acme Insight's supply-chain visibility use case.",
                "match_strength": "74",
            },
        ]
    }
)


def _load_system_prompt():
    return PROMPT_FILE.read_text(encoding="utf-8")


def call_agent_2(startup_profile, companies):
    """Return a list of match dicts (name, url, reasoning, match_strength).

    ``startup_profile`` is the dict from Agent 1; ``companies`` is the parsed
    candidate list from companies.json.
    """
    # Static content (instructions + candidate companies) goes in the cached
    # system block. Only the per-startup profile varies per call.
    companies_json = json.dumps(companies, ensure_ascii=False, indent=2)
    cached_system = (
        f"{_load_system_prompt()}\n\nCANDIDATE COMPANIES:\n{companies_json}\n\n"
        "The startup profile to evaluate against these candidates is provided "
        "in the user message."
    )

    startup_json = json.dumps(startup_profile, ensure_ascii=False)
    user_content = f"STARTUP PROFILE:\n{startup_json}"

    raw = call_claude(
        system_prompt=cached_system,
        user_content=user_content,
        model=SMART_MODEL,
        max_tokens=AGENT2_MAX_TOKENS,
        mock_response=_MOCK_MATCHES,
    )

    parsed = extract_json(raw)
    if isinstance(parsed, dict):
        return parsed.get("matches", [])
    return parsed
