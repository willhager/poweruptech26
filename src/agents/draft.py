"""Agent 3: draft an intro email to each matched company."""

import json

from config import FAST_MODEL, AGENT3_MAX_TOKENS, PROMPTS_DIR
from ..claude_client import call_claude, extract_json

PROMPT_FILE = PROMPTS_DIR / "draft.txt"

_MOCK_DRAFTS = json.dumps(
    [
        {
            "company_name": "Northbridge Analytics",
            "match_strength": "88",
            "compatibility_reasoning": "As an enterprise data analytics consulting firm, Northbridge has clients who need faster operational reporting.",
            "email_draft": "Hi Elena, your team helps enterprises make confident decisions from their data. Acme Insight plugs into messy operational data and turns it into decision-ready dashboards with automated anomaly detection, so your clients spend less time wrangling reports. Open to a 15-minute call this week? — Acme Insight Team",
        }
    ]
)


def _load_system_prompt():
    return PROMPT_FILE.read_text(encoding="utf-8")


def build_startup_paragraph(profile):
    """Collapse Agent 1's structured profile into the short paragraph Agent 3 wants."""
    sp = profile.get("startup_profile", profile) if isinstance(profile, dict) else {}
    name = sp.get("company_name") or "The startup"
    summary = sp.get("summary") or sp.get("company_description") or ""
    industries = ", ".join(sp.get("industries_served", []) or [])
    customers = ", ".join(sp.get("target_customers", []) or [])

    parts = [f"{name}: {summary}".strip().rstrip(":")]
    if industries:
        parts.append(f"Industries served: {industries}.")
    if customers:
        parts.append(f"Target customers: {customers}.")
    return " ".join(p for p in parts if p)


def call_agent_3(startup_paragraph, matches):
    """Return a list of draft dicts (company_name, match_strength, reasoning, email_draft)."""
    matches_json = json.dumps(matches, ensure_ascii=False, indent=2)
    user_content = (
        f"STARTUP:\n{startup_paragraph}\n\n"
        f"TARGET COMPANIES:\n{matches_json}"
    )

    raw = call_claude(
        system_prompt=_load_system_prompt(),
        user_content=user_content,
        model=FAST_MODEL,
        max_tokens=AGENT3_MAX_TOKENS,
        mock_response=_MOCK_DRAFTS,
    )

    return extract_json(raw)
