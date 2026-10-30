"""Generic HTTP SMS provider — POSTs to a configured endpoint."""

from __future__ import annotations

import logging

import requests

from core.sms.base import SmsProvider

logger = logging.getLogger("core.sms.http")


class HttpGenericSmsProvider(SmsProvider):
    def __init__(self, *, api_url: str, api_key: str = "", sender_id: str = ""):
        self.api_url = (api_url or "").strip()
        self.api_key = (api_key or "").strip()
        self.sender_id = (sender_id or "").strip()

    def send(self, to: str, message: str) -> bool:
        if not self.api_url:
            logger.error("HTTP SMS provider missing api_url")
            return False
        payload = {
            "to": to,
            "message": message,
        }
        if self.sender_id:
            payload["sender"] = self.sender_id
            payload["from"] = self.sender_id
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=15,
            )
            if 200 <= response.status_code < 300:
                return True
            logger.error(
                "HTTP SMS failed status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            return False
        except requests.RequestException as exc:
            logger.exception("HTTP SMS request error: %s", exc)
            return False
