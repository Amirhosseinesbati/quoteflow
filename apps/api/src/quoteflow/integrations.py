"""External connector interfaces and adapters."""

from __future__ import annotations

from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import LocalCRMRecord, OutboxEvent


class CRMConnector(Protocol):
    def upsert_accepted_deal(
        self, *, client_email: str, client_name: str, quote_id: str, total: str
    ) -> str: ...


class HubSpotConnector:
    BASE = "https://api.hubapi.com"

    def __init__(self, access_token: str, client: httpx.Client | None = None):
        if not access_token:
            raise ValueError("HUBSPOT_ACCESS_TOKEN is required")
        self.client = client or httpx.Client(base_url=self.BASE, timeout=15)
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def upsert_accepted_deal(
        self, *, client_email: str, client_name: str, quote_id: str, total: str
    ) -> str:
        contact = self.client.post(
            "/crm/v3/objects/contacts/batch/upsert",
            headers=self.headers,
            json={
                "inputs": [
                    {
                        "id": client_email,
                        "idProperty": "email",
                        "properties": {"email": client_email, "firstname": client_name},
                    }
                ]
            },
        )
        contact.raise_for_status()
        deal = self.client.post(
            "/crm/v3/objects/deals",
            headers=self.headers,
            json={
                "properties": {
                    "dealname": f"QuoteFlow {quote_id}",
                    "amount": total,
                    "description": f"QuoteFlow accepted quote {quote_id}",
                }
            },
        )
        deal.raise_for_status()
        return str(deal.json()["id"])


def record_local_handoff(
    session: Session,
    *,
    workspace_id: str,
    client_id: str,
    version_id: str,
    quote_id: str,
    total: str,
) -> None:
    existing = session.scalar(
        select(LocalCRMRecord).where(LocalCRMRecord.quote_version_id == version_id)
    )
    if existing is None:
        session.add(
            LocalCRMRecord(
                workspace_id=workspace_id, client_id=client_id, quote_version_id=version_id
            )
        )
    key = f"crm-handoff:{version_id}"
    if session.scalar(select(OutboxEvent).where(OutboxEvent.idempotency_key == key)) is None:
        session.add(
            OutboxEvent(
                workspace_id=workspace_id,
                event_type="crm.accepted_quote",
                idempotency_key=key,
                payload={"quote_id": quote_id, "version_id": version_id, "total": total},
            )
        )
