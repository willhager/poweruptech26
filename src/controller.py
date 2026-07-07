"""End-to-end orchestrator for the startup <-> company matching pipeline.

Flow:
    Gmail inbox  ->  Agent 1 (extract profile)
                 ->  Agent 2 (match against companies.json, with reasoning)
                 ->  Agent 3 (draft outreach emails)
"""

import json
import shutil

from config import (
    COMPANIES_FILE,
    INCOMING_DIR,
    PROCESSED_DIR,
    RESULTS_DIR,
)
from .inbox import ReadEmailInbox
from .agents.extract import process_email
from .agents.match import call_agent_2
from .agents.draft import call_agent_3, build_startup_paragraph
from datetime import datetime

from send_report import build_message, resolve_recipient, send_message


def load_companies():
    return json.loads(COMPANIES_FILE.read_text(encoding="utf-8"))


def build_contact_lookup(companies):
    """Map company name -> primary contact info, so drafts get a real recipient."""
    lookup = {}
    for c in companies:
        personnel = c.get("contact_personnel") or [{}]
        lookup[c.get("company")] = personnel[0]
    return lookup


def enrich_drafts(drafts, contact_lookup):
    """Attach recipient contact details (from companies.json) to each draft."""
    for d in drafts:
        contact = contact_lookup.get(d.get("company_name"), {})
        d["recipient"] = {
            "name": contact.get("name"),
            "role": contact.get("role"),
            "email": contact.get("email"),
        }
    return drafts


def run_pipeline_on_email(email_path, companies, contact_lookup):
    print(f"\n=== Processing {email_path.name} ===")

    # Agent 1: raw email -> structured startup profile
    profile = process_email(str(email_path))
    startup_name = (
        profile.get("startup_profile", {}).get("company_name")
        if isinstance(profile, dict)
        else None
    ) or "(unknown startup)"
    print(f"Agent 1 -> extracted profile for: {startup_name}")

    # Agent 2: profile + candidate companies -> matches with reasoning
    matches = call_agent_2(profile, companies)
    print(f"Agent 2 -> {len(matches)} match(es):")
    for m in matches:
        print(f"  - {m.get('name')} (strength {m.get('match_strength')})")
        print(f"      why: {m.get('reasoning')}")

    if not matches:
        print("No plausible matches; skipping email drafting.")
        drafts = []
    else:
        # Agent 3: startup paragraph + matches -> drafted outreach emails
        paragraph = build_startup_paragraph(profile)
        drafts = call_agent_3(paragraph, matches)
        drafts = enrich_drafts(drafts, contact_lookup)
        print(f"Agent 3 -> {len(drafts)} draft email(s) generated.")

    return {
        "source_email": email_path.name,
        "startup_profile": profile,
        "matches": matches,
        "drafts": drafts,
    }


def save_result(result):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = result["source_email"].rsplit(".", 1)[0]
    out_path = RESULTS_DIR / f"result_{stem}_{timestamp}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved results -> {out_path}")


def archive_email(email_path):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(email_path), str(PROCESSED_DIR / email_path.name))


def send_report_email(result):
    """Email the formatted match report back to the original sender.

    Failures here are logged but not raised, so a send problem never loses the
    results we already computed and saved.
    """
    try:
        recipient = resolve_recipient(result)
        if not recipient:
            print("Report not sent: could not determine a recipient.")
            return
        msg = build_message(result, recipient)
        send_message(msg)
        print(f"Report email -> sent to {recipient}")
    except Exception as exc:
        print(f"Report email FAILED: {exc}")


def main(fetch=True, send=True):
    if fetch:
        ReadEmailInbox()

    companies = load_companies()
    contact_lookup = build_contact_lookup(companies)

    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    email_files = sorted(INCOMING_DIR.glob("*.txt"))
    if not email_files:
        print("No emails to process in runtime/incoming/.")
        return

    for email_path in email_files:
        try:
            result = run_pipeline_on_email(email_path, companies, contact_lookup)
            save_result(result)
            if send:
                # Send before archiving so the source email's From header is
                # still resolvable (resolve_recipient also checks processed/).
                send_report_email(result)
            archive_email(email_path)
        except Exception as exc:  # keep processing remaining emails
            print(f"ERROR processing {email_path.name}: {exc}")
