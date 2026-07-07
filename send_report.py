import argparse
import json
import re
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from email.utils import parseaddr
from html import escape
from pathlib import Path

# Reuse the same Gmail account the inbox reader logs in with, configured via
# the .env file (EMAIL_ADDRESS / EMAIL_PASSWORD).
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, INCOMING_DIR, PROCESSED_DIR, RESULTS_DIR

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


# --- Loading ---------------------------------------------------------------
def latest_result_file():
    """Return the most recently modified result JSON, or None if there are none."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    candidates = sorted(
        RESULTS_DIR.glob("result_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load_result(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_profile(result):
    """Return the innermost startup_profile dict, tolerating the double-nesting.

    Agent 1's output is stored as result["startup_profile"], which itself often
    wraps another {"startup_profile": {...}} object, so unwrap up to two levels.
    """
    node = result.get("startup_profile", {}) or {}
    for _ in range(2):
        if isinstance(node, dict) and "startup_profile" in node:
            node = node["startup_profile"]
        else:
            break
    return node if isinstance(node, dict) else {}


# --- Recipient resolution --------------------------------------------------
def sender_from_source_email(source_email_name):
    """Parse the 'From:' header out of the original saved email file, if present."""
    if not source_email_name:
        return None
    for folder in (INCOMING_DIR, PROCESSED_DIR):
        path = Path(folder) / source_email_name
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.lower().startswith("from:"):
                    addr = parseaddr(line.split(":", 1)[1])[1]
                    if addr:
                        return addr
                if not line.strip():
                    break  # headers end at the first blank line
    return None


def resolve_recipient(result, override=None):
    if override:
        return override
    from_source = sender_from_source_email(result.get("source_email"))
    if from_source:
        return from_source
    contact = get_profile(result).get("contact", {}) or {}
    return contact.get("email")


# --- Formatting ------------------------------------------------------------
def _clean(value, default=""):
    return value if value not in (None, "") else default


def build_plain_text(result):
    profile = get_profile(result)
    company = _clean(profile.get("company_name"), "your startup")
    contact = profile.get("contact", {}) or {}
    contact_name = _clean(contact.get("contact_name"))

    matches = result.get("matches", []) or []
    drafts = result.get("drafts", []) or []
    drafts_by_company = {d.get("company_name"): d for d in drafts}

    lines = []
    greeting = f"Hi {contact_name}," if contact_name else "Hello,"
    lines.append(greeting)
    lines.append("")
    lines.append(
        f"Here are the partner matches we found for {company}, ranked by how "
        f"strong the fit looks. Each match includes our reasoning and a ready-to-send "
        f"draft you can use to reach out."
    )
    lines.append("")

    if not matches:
        lines.append("No plausible matches were found for this profile.")
    for i, m in enumerate(matches, start=1):
        name = _clean(m.get("name"), "(unnamed company)")
        url = _clean(m.get("url"))
        strength = m.get("match_strength")
        reasoning = _clean(m.get("reasoning"))

        header = f"{i}. {name}"
        if strength is not None:
            header += f"  —  match strength: {strength}/100"
        lines.append(header)
        lines.append("-" * len(header))
        if url:
            lines.append(f"Website: {url}")
        if reasoning:
            lines.append("")
            lines.append(f"Why it's a fit: {reasoning}")

        draft = drafts_by_company.get(m.get("name"))
        if draft:
            recipient = draft.get("recipient", {}) or {}
            r_name = _clean(recipient.get("name"))
            r_role = _clean(recipient.get("role"))
            r_email = _clean(recipient.get("email"))
            to_bits = " ".join(b for b in [r_name, f"({r_role})" if r_role else "", r_email] if b)
            lines.append("")
            if to_bits:
                lines.append(f"Suggested contact: {to_bits}")
            lines.append("Draft email:")
            lines.append("")
            lines.append(_clean(draft.get("email_draft")))
        lines.append("")
        lines.append("")

    lines.append("— PowerUp Tech matching pipeline")
    return "\n".join(lines).rstrip() + "\n"


def build_html(result):
    profile = get_profile(result)
    company = escape(_clean(profile.get("company_name"), "your startup"))
    contact = profile.get("contact", {}) or {}
    contact_name = escape(_clean(contact.get("contact_name")))

    matches = result.get("matches", []) or []
    drafts = result.get("drafts", []) or []
    drafts_by_company = {d.get("company_name"): d for d in drafts}

    greeting = f"Hi {contact_name}," if contact_name else "Hello,"

    parts = [
        "<div style=\"font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
        "color:#1a1a1a;max-width:640px;margin:0 auto;line-height:1.5;\">",
        f"<p>{greeting}</p>",
        f"<p>Here are the partner matches we found for <strong>{company}</strong>, "
        "ranked by how strong the fit looks. Each match includes our reasoning and a "
        "ready-to-send draft you can use to reach out.</p>",
    ]

    if not matches:
        parts.append("<p><em>No plausible matches were found for this profile.</em></p>")

    for i, m in enumerate(matches, start=1):
        name = escape(_clean(m.get("name"), "(unnamed company)"))
        url = _clean(m.get("url"))
        strength = m.get("match_strength")
        reasoning = escape(_clean(m.get("reasoning")))

        parts.append(
            "<div style=\"border:1px solid #e3e3e3;border-radius:10px;padding:16px 20px;"
            "margin:18px 0;background:#fafafa;\">"
        )
        strength_badge = ""
        if strength is not None:
            strength_badge = (
                "<span style=\"display:inline-block;background:#0b7285;color:#fff;"
                "border-radius:999px;padding:2px 10px;font-size:13px;font-weight:600;"
                f"margin-left:8px;\">{escape(str(strength))}/100</span>"
            )
        parts.append(
            f"<h3 style=\"margin:0 0 4px;font-size:18px;\">{i}. {name}{strength_badge}</h3>"
        )
        if url:
            href = url if url.startswith("http") else f"https://{url}"
            parts.append(
                f"<div style=\"font-size:14px;margin-bottom:8px;\">"
                f"<a href=\"{escape(href)}\" style=\"color:#0b7285;\">{escape(url)}</a></div>"
            )
        if reasoning:
            parts.append(
                f"<p style=\"margin:8px 0;\"><strong>Why it's a fit:</strong> {reasoning}</p>"
            )

        draft = drafts_by_company.get(m.get("name"))
        if draft:
            recipient = draft.get("recipient", {}) or {}
            r_name = escape(_clean(recipient.get("name")))
            r_role = escape(_clean(recipient.get("role")))
            r_email = escape(_clean(recipient.get("email")))
            to_bits = " ".join(
                b for b in [r_name, f"({r_role})" if r_role else "", r_email] if b
            )
            draft_body = escape(_clean(draft.get("email_draft"))).replace("\n", "<br>")
            if to_bits:
                parts.append(
                    f"<p style=\"margin:8px 0 4px;font-size:14px;color:#555;\">"
                    f"<strong>Suggested contact:</strong> {to_bits}</p>"
                )
            parts.append(
                "<div style=\"background:#fff;border-left:3px solid #0b7285;"
                "padding:10px 14px;margin-top:8px;font-size:14px;color:#333;\">"
                f"{draft_body}</div>"
            )
        parts.append("</div>")

    parts.append(
        "<p style=\"color:#888;font-size:13px;margin-top:24px;\">— PowerUp Tech "
        "matching pipeline</p>"
    )
    parts.append("</div>")
    return "\n".join(parts)


def build_subject(result):
    profile = get_profile(result)
    company = _clean(profile.get("company_name"), "your startup")
    n = len(result.get("matches", []) or [])
    plural = "match" if n == 1 else "matches"
    return f"Your partner matches for {company} ({n} {plural})"


# --- Sending ---------------------------------------------------------------
def build_message(result, recipient):
    msg = EmailMessage()
    msg["Subject"] = build_subject(result)
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient
    msg.set_content(build_plain_text(result))
    msg.add_alternative(build_html(result), subtype="html")
    return msg


def send_message(msg):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise SystemExit(
            "EMAIL_ADDRESS and EMAIL_PASSWORD must be set (see .env). "
            "Use a Gmail app password, not your account password."
        )
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "result",
        nargs="?",
        help="Path to a result JSON. Defaults to the newest file in runtime/results/.",
    )
    parser.add_argument("--to", help="Override the recipient email address.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the composed email instead of sending it.",
    )
    args = parser.parse_args(argv)

    result_path = Path(args.result) if args.result else latest_result_file()
    if not result_path or not Path(result_path).exists():
        parser.error(
            "No result JSON found. Pass a path or run the pipeline first "
            "(nothing in runtime/results/)."
        )

    result = load_result(result_path)
    recipient = resolve_recipient(result, override=args.to)
    if not recipient:
        parser.error(
            "Could not determine a recipient. Use --to to set one explicitly "
            "(no source email 'From' header and no contact email in the profile)."
        )

    msg = build_message(result, recipient)

    print(f"Result file : {result_path}")
    print(f"Recipient   : {recipient}")
    print(f"Subject     : {msg['Subject']}")

    if args.dry_run:
        print("\n----- PLAIN TEXT -----\n")
        print(build_plain_text(result))
        print("(dry run: nothing was sent)")
        return

    send_message(msg)
    print("Email sent.")


if __name__ == "__main__":
    main()
