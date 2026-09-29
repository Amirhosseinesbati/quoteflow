"""Redact customer bearer tokens before Uvicorn writes access records."""

from __future__ import annotations

import logging
import re
from typing import Any

_PORTAL_TOKEN = re.compile(r"(?P<route>/api/portal/)[^/?#\s]+", re.IGNORECASE)


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _PORTAL_TOKEN.sub(r"\g<route>[REDACTED]", value)
    if isinstance(value, bytes):
        return _redact(value.decode("utf-8", errors="replace"))
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    return value


class PortalTokenRedactionFilter(logging.Filter):
    """Scrub both formatted and parameterized Uvicorn access messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(record.msg)
        record.args = _redact(record.args)
        return True


def install_access_log_redaction() -> None:
    """Install once; safe to call again after Uvicorn configures logging."""

    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, PortalTokenRedactionFilter) for item in logger.filters):
        logger.addFilter(PortalTokenRedactionFilter())
