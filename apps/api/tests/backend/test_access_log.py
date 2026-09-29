"""Access logs must never contain customer portal bearer tokens."""

from __future__ import annotations

import logging

from quoteflow.access_log import PortalTokenRedactionFilter, install_access_log_redaction


def test_uvicorn_access_log_redacts_portal_token_and_keeps_route_shape():
    logger = logging.getLogger("uvicorn.access")
    install_access_log_redaction()
    install_access_log_redaction()
    assert sum(isinstance(item, PortalTokenRedactionFilter) for item in logger.filters) == 1

    token = "opaque-fixture-token"
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1", "POST", f"/api/portal/{token}/response?reply=yes", "1.1", 200),
        exc_info=None,
    )
    for item in logger.filters:
        assert item.filter(record)
    message = record.getMessage()
    assert token not in message
    assert "/api/portal/[REDACTED]/response?reply=yes" in message

    preformatted = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=f"GET /api/portal/{token} HTTP/1.1",
        args=(),
        exc_info=None,
    )
    for item in logger.filters:
        assert item.filter(preformatted)
    assert token not in preformatted.getMessage()
