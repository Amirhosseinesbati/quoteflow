"""Durable outbox processor; ambiguous connector outcomes stop for reconciliation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .integrations import HubSpotConnector
from .models import Client, OutboxEvent, Quote


def recover_expired_leases(db: Session) -> int:
    current = datetime.now(UTC)
    rows = db.scalars(
        select(OutboxEvent).where(
            OutboxEvent.status == "processing", OutboxEvent.lease_until < current
        )
    ).all()
    for event in rows:
        event.status = "uncertain"
        event.last_error = "Worker lease expired; check provider before retrying"
        event.lease_until = None
    db.commit()
    return len(rows)


def process_outbox_once(db: Session, connector: HubSpotConnector | None = None) -> dict:
    settings = get_settings()
    recovered = recover_expired_leases(db)
    if settings.mode.upper() == "DEMO":
        return {
            "processed": 0,
            "recovered_uncertain": recovered,
            "reason": "DEMO records outbox events without external sends",
        }
    if not settings.hubspot_enabled:
        return {
            "processed": 0,
            "recovered_uncertain": recovered,
            "reason": "HubSpot is not enabled",
        }
    event = db.scalar(
        select(OutboxEvent)
        .where(
            OutboxEvent.status == "pending",
            OutboxEvent.event_type == "crm.accepted_quote",
            OutboxEvent.next_attempt_at.is_(None)
            | (OutboxEvent.next_attempt_at <= datetime.now(UTC)),
        )
        .order_by(OutboxEvent.created_at)
        .with_for_update(skip_locked=True)
    )
    if event is None:
        return {"processed": 0, "recovered_uncertain": recovered}
    if connector is None:
        connector = HubSpotConnector(settings.hubspot_access_token)
    event.status = "processing"
    event.attempts += 1
    event.lease_until = datetime.now(UTC) + timedelta(minutes=5)
    event.next_attempt_at = None
    db.commit()
    quote = db.get(Quote, event.payload["quote_id"])
    client = db.get(Client, quote.client_id) if quote else None
    if quote is None or client is None or quote.workspace_id != event.workspace_id:
        event.status = "failed"
        event.last_error = "Scoped quote/client for outbox event is missing"
        event.lease_until = None
        db.commit()
        return {"processed": 1, "status": event.status}
    try:
        provider_id = connector.upsert_accepted_deal(
            client_email=client.contact_email,
            client_name=client.contact_name or client.name,
            quote_id=quote.id,
            total=event.payload["total"],
        )
        event.status = "delivered"
        event.provider_id = provider_id
        event.last_error = ""
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 429 and event.attempts < settings.hubspot_max_attempts:
            event.status = "pending"
            wait_seconds = min(settings.worker_backoff_seconds * (2 ** (event.attempts - 1)), 3600)
            event.next_attempt_at = datetime.now(UTC) + timedelta(seconds=wait_seconds)
        else:
            event.status = "failed" if code < 500 else "uncertain"
        event.last_error = f"HubSpot HTTP {code}"
    except (httpx.RequestError, TimeoutError) as exc:
        event.status = "uncertain"
        event.last_error = f"Ambiguous connector outcome: {type(exc).__name__}"
    event.lease_until = None
    db.commit()
    return {"processed": 1, "status": event.status, "event_id": event.id}
