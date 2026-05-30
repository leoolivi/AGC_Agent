"""SMTPAdapter — email sending via SMTP."""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from app.core.ports.email import EmailMessage, EmailSenderPort

logger = structlog.get_logger()


class SMTPAdapter(EmailSenderPort):
    def __init__(self, host: str, port: int, user: str, password: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password

    async def send(self, message: EmailMessage) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = self._user
            msg["To"] = ", ".join(message.to)
            if message.reply_to:
                msg["Reply-To"] = message.reply_to
            msg.attach(MIMEText(message.body_text, "plain"))
            msg.attach(MIMEText(message.body_html, "html"))

            with smtplib.SMTP(self._host, self._port) as server:
                server.starttls()
                server.login(self._user, self._password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error("smtp_send_failed", error=str(e))
            return False

    async def send_draft(self, draft_id: str) -> bool:
        # In production, load draft from DB and call send()
        logger.info("smtp_send_draft", draft_id=draft_id)
        return True
