from __future__ import annotations
from dataclasses import dataclass
from email.message import EmailMessage
import json
import os
import smtplib
import urllib.request
from typing import Any, Callable


@dataclass(frozen=True)
class NotificationConfig:
    enabled: bool
    discord_webhook_url: str
    slack_webhook_url: str
    telegram_bot_token: str
    telegram_chat_id: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    email_from: str
    email_to: str

    @property
    def configured_channels(self) -> list[str]:
        channels = []
        if self.discord_webhook_url:
            channels.append("discord")
        if self.slack_webhook_url:
            channels.append("slack")
        if self.telegram_bot_token and self.telegram_chat_id:
            channels.append("telegram")
        if self.smtp_host and self.email_from and self.email_to:
            channels.append("email")
        return channels


def load_notification_config() -> NotificationConfig:
    return NotificationConfig(
        enabled=os.getenv(
            "BOT_NOTIFICATIONS_ENABLE", ""
        ).lower() == "true",
        discord_webhook_url=os.getenv(
            "BOT_DISCORD_WEBHOOK_URL", ""
        ),
        slack_webhook_url=os.getenv(
            "BOT_SLACK_WEBHOOK_URL", ""
        ),
        telegram_bot_token=os.getenv(
            "BOT_TELEGRAM_BOT_TOKEN", ""
        ),
        telegram_chat_id=os.getenv(
            "BOT_TELEGRAM_CHAT_ID", ""
        ),
        smtp_host=os.getenv("BOT_SMTP_HOST", ""),
        smtp_port=int(os.getenv("BOT_SMTP_PORT", "587")),
        smtp_username=os.getenv("BOT_SMTP_USERNAME", ""),
        smtp_password=os.getenv("BOT_SMTP_PASSWORD", ""),
        email_from=os.getenv("BOT_EMAIL_FROM", ""),
        email_to=os.getenv("BOT_EMAIL_TO", ""),
    )


class NotificationCenter:
    def __init__(
        self,
        config: NotificationConfig,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        smtp_factory: Callable[..., Any] = smtplib.SMTP,
    ) -> None:
        self.config = config
        self.opener = opener
        self.smtp_factory = smtp_factory

    def send(self, subject: str, message: str) -> dict[str, Any]:
        if not self.config.enabled:
            return {
                "status": "DISABLED",
                "sent_channels": [],
                "configured_channels": (
                    self.config.configured_channels
                ),
            }

        sent = []
        errors = []

        for channel in self.config.configured_channels:
            try:
                if channel == "discord":
                    self._webhook(
                        self.config.discord_webhook_url,
                        {"content": f"**{subject}**\n{message}"},
                    )
                elif channel == "slack":
                    self._webhook(
                        self.config.slack_webhook_url,
                        {"text": f"*{subject}*\n{message}"},
                    )
                elif channel == "telegram":
                    token = self.config.telegram_bot_token
                    url = (
                        f"https://api.telegram.org/bot{token}/"
                        "sendMessage"
                    )
                    self._webhook(url, {
                        "chat_id": self.config.telegram_chat_id,
                        "text": f"{subject}\n{message}",
                    })
                elif channel == "email":
                    self._email(subject, message)
                sent.append(channel)
            except Exception as exc:
                errors.append({
                    "channel": channel,
                    "error": str(exc),
                })

        return {
            "status": "PASS" if not errors else "PARTIAL_FAILURE",
            "sent_channels": sent,
            "errors": errors,
        }

    def _webhook(self, url: str, payload: dict[str, Any]) -> None:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.opener(request, timeout=10) as response:
            response.read()

    def _email(self, subject: str, message: str) -> None:
        mail = EmailMessage()
        mail["Subject"] = subject
        mail["From"] = self.config.email_from
        mail["To"] = self.config.email_to
        mail.set_content(message)

        with self.smtp_factory(
            self.config.smtp_host,
            self.config.smtp_port,
            timeout=10,
        ) as smtp:
            smtp.starttls()
            if self.config.smtp_username:
                smtp.login(
                    self.config.smtp_username,
                    self.config.smtp_password,
                )
            smtp.send_message(mail)
