"""Compatibility re-export; canonical protocol lives in :mod:`services.backend_client_protocol`."""

from __future__ import annotations

from services.backend_client_protocol import BackendClient

__all__ = ["BackendClient"]
