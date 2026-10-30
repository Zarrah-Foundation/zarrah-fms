"""Console SMS provider — logs only, never sends a real message."""

import logging

from core.sms.base import SmsProvider

logger = logging.getLogger("core.sms.console")


class ConsoleSmsProvider(SmsProvider):
    def send(self, to: str, message: str) -> bool:
        logger.info("SMS console (not sent) to=%s message=%s", to, message)
        return True
