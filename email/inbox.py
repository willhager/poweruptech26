import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime

IMAP_SERVER = "imap.google.com"
EMAIL_ADDRESS = ""
EMAIL_PASSWORD = ""

OUTPUT_DIR = r"IncomingEmails"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def decode_email_header(value):
    if not value:
        return ""
    
    decoded_parts = decode_header(value)
    result = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="ignore")
        else:
            result += part

    return result

mail = imaplib.IMAP4_SSL(IMAP_SERVER)
print("Connected")
mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

mail.select("INBOX")

status, messages = mail.search(None, "UNSEEN")

email_ids = messages[0].split()

for email_id in email_ids:
    status, msg_data = mail.fetch(email_id, "(RFC822)")

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    subject = decode_email_header(msg["Subject"])
    sender = decode_email_header(msg["From"])
    date = msg["Date"]

    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()

            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8",
                        errors="ignore"
                    )
                    break
                except Exception:
                    pass
    else:
        body = msg.get_payload(decode=True).decode(
            msg.get_content_charset() or "utf-8",
            errors="ignore"
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"email_{timestamp}_{email_id.decode()}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"From: {sender}\n")
        f.write(f"Subject: {subject}\n")
        f.write(f"Date: {date}\n")
        f.write("\n")
        f.write(body)

    print(f"Saved: {filepath}")

    mail.store(email_id, '+FLAGS', '\\Seen')

mail.logout()
