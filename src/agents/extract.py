"""Agent 1: turn a raw startup email into a structured startup-profile JSON."""

import json
from pathlib import Path
from datetime import datetime

from config import FAST_MODEL, AGENT1_MAX_TOKENS, PROMPTS_DIR, DEBUG_DIR
from ..claude_client import call_claude, extract_json

PROMPT_FILE = PROMPTS_DIR / "extract.txt"

# Canned output for MOCK_CLAUDE mode so the rest of the pipeline has something
# realistic to chew on without spending credits.
_MOCK_PROFILE = json.dumps(
    {
        "startup_profile": {
            "company_name": "Acme Insight",
            "company_description": "AI-powered analytics for mid-market operations teams.",
            "summary": "Acme Insight helps companies turn messy operational data into clear, decision-ready dashboards.",
            "services_offered": [
                {
                    "service_name": "Operational analytics platform",
                    "description": "Automated dashboards and anomaly detection.",
                    "keywords": ["analytics", "dashboards", "data"],
                }
            ],
            "products_offered": [],
            "industries_served": ["Logistics", "Finance", "Data Analytics"],
            "target_customers": ["Enterprise operations teams"],
            "ideal_business_partners": ["Data-heavy enterprises"],
            "business_needs": ["Design partners", "Pilot customers"],
            "partnership_goals": ["Land 3 enterprise pilots"],
            "problems_they_solve": ["Fragmented, slow operational reporting"],
            "geographic_preferences": {
                "startup_location": None,
                "desired_regions": [],
                "remote_or_local_preference": "remote",
            },
            "company_stage": {"stage": "seed", "funding_status": None, "company_size": "small"},
            "timeline": {"available_start_date": None, "urgency": "medium", "timeline_notes": None},
            "contact": {
                "contact_name": None,
                "title": None,
                "email": None,
                "phone": None,
                "website": None,
                "linkedin": None,
                "other_contact_details": [],
            },
            "important_keywords": ["analytics", "operations", "data intelligence"],
            "matching_signals": {
                "good_fit_company_traits": ["Large operational data footprint"],
                "likely_buyer_departments": ["Operations", "Data Analytics"],
                "relevant_enterprise_use_cases": ["Supply chain visibility"],
                "required_capabilities_from_partner": [],
            },
            "missing_information": [],
            "uncertainties": [],
            "source_evidence": [],
        }
    }
)


def _load_system_prompt():
    """The static instructions (everything before the email placeholder)."""
    template = PROMPT_FILE.read_text(encoding="utf-8")
    return template.split("{{EMAIL_TEXT}}")[0].strip()


def process_email(email_file_path):
    """Extract a structured startup profile (dict) from a saved email file."""
    email_content = Path(email_file_path).read_text(encoding="utf-8")

    system_prompt = _load_system_prompt()
    raw = call_claude(
        system_prompt=system_prompt,
        user_content=email_content,
        model=FAST_MODEL,
        max_tokens=AGENT1_MAX_TOKENS,
        mock_response=_MOCK_PROFILE,
    )

    profile = extract_json(raw)

    _save_debug(email_file_path, raw)
    return profile


def _save_debug(email_file_path, raw_response):
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(email_file_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (DEBUG_DIR / f"agent1_{stem}_{timestamp}.json").write_text(
        raw_response, encoding="utf-8"
    )
