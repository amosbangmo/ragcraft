"""Gateway-local factories for UI-bound services (e.g. chat transcript)."""

from services.factories.chat_service_factory import build_chat_service

__all__ = ["build_chat_service"]
