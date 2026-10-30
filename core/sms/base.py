"""SMS provider interface."""

from abc import ABC, abstractmethod


class SmsProvider(ABC):
    """Minimal provider contract used by :class:`SMSService`."""

    @abstractmethod
    def send(self, to: str, message: str) -> bool:
        """Deliver ``message`` to ``to``. Return True on success."""
