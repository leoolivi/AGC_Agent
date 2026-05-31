"""Gmail adapter — send and read emails via Gmail API."""
from __future__ import annotations

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog
from googleapiclient.discovery import build

from app.adapters.google.credentials import get_credentials
from app.core.ports.email import EmailMessage, EmailSenderPort

logger = structlog.get_logger()


class GmailSenderAdapter(EmailSenderPort):
    """Send emails via Gmail API."""

    async def send(self, message: EmailMessage, user_id: str = "") -> bool:
        try:
            creds = await get_credentials(user_id)
            service = build("gmail", "v1", credentials=creds)

            msg = MIMEMultipart("alternative")
            msg["To"] = ", ".join(message.to)
            msg["Subject"] = message.subject
            if message.reply_to:
                msg["Reply-To"] = message.reply_to
            msg.attach(MIMEText(message.body_text, "plain"))
            msg.attach(MIMEText(message.body_html, "html"))

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
            logger.info("gmail_sent", to=message.to, subject=message.subject)
            return True
        except Exception as e:
            logger.error("gmail_send_failed", error=str(e))
            return False

    async def send_draft(self, draft_id: str) -> bool:
        return True  # Handled by send() with draft content


class GmailReaderAdapter:
    """Read emails from Gmail inbox."""

    async def fetch_messages(self, user_id: str, max_results: int = 10, query: str = "") -> list[dict]:
        try:
            creds = await get_credentials(user_id)
            service = build("gmail", "v1", credentials=creds)

            q = query or "is:inbox"
            result = service.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
            messages = result.get("messages", [])

            emails: list[dict] = []
            for msg_ref in messages:
                msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]).execute()
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                emails.append({
                    "id": msg["id"],
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                    "snippet": msg.get("snippet", ""),
                })
            return emails
        except Exception as e:
            logger.error("gmail_read_failed", error=str(e))
            return []

    async def get_message(self, user_id: str, message_id: str) -> dict | None:
        try:
            creds = await get_credentials(user_id)
            service = build("gmail", "v1", credentials=creds)
            msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()

            # Extract body
            payload = msg.get("payload", {})
            body_text = ""
            if payload.get("parts"):
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                        body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode()
                        break
            elif payload.get("body", {}).get("data"):
                body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode()

            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
            return {
                "id": msg["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body_text,
            }
        except Exception as e:
            logger.error("gmail_get_message_failed", error=str(e))
            return None
