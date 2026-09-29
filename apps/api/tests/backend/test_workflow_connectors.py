from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import select

from quoteflow.config import get_settings
from quoteflow.integrations import HubSpotConnector
from quoteflow.main import app
from quoteflow.models import Brief, OutboxEvent, Quote
from quoteflow.worker import process_outbox_once
from quoteflow.workflow import build_workflow


def test_graph_interrupt_and_scoped_resume(api, monkeypatch):
    client, factory = api
    monkeypatch.setattr("quoteflow.workflow.SessionLocal", factory)
    app.state.quote_workflow = build_workflow(InMemorySaver())
    assert client.post("/api/auth/demo", json={"role": "operator"}).status_code == 200
    created = client.post(
        "/api/briefs",
        json={
            "text": "We need a website and CRM form. We can supply our logo.",
            "company_name": "Test Client",
        },
    )
    brief_id = created.json()["id"]
    started = client.post(f"/api/workflows/briefs/{brief_id}/start")
    assert started.status_code == 201, started.text
    assert started.json()["status"] == "waiting_clarification"
    questions = started.json()["interrupt"]["questions"]
    assert questions
    job_id = started.json()["id"]
    assert (
        client.post(
            "/api/auth/demo", json={"workspace": "arc-field-isolation", "role": "operator"}
        ).status_code
        == 200
    )
    assert client.get(f"/api/workflows/{job_id}").status_code == 404
    assert client.post("/api/auth/demo", json={"role": "operator"}).status_code == 200
    answers = {question["id"]: "Twelve weeks and $15,000-$25,000" for question in questions}
    resumed = client.post(f"/api/workflows/{job_id}/resume", json={"answers": answers})
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "waiting_internal_review"
    assert len(resumed.json()["interrupt"]["option_ids"]) == 3
    assert (
        client.post(
            f"/api/workflows/{job_id}/resume",
            json={"version_id": resumed.json()["interrupt"]["option_ids"][0]},
        ).status_code
        == 403
    )
    cancelled = client.post(f"/api/workflows/{job_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.post(f"/api/workflows/{job_id}/resume", json={}).status_code == 409


def test_connected_mode_rejects_demo_password(api, monkeypatch):
    client, _ = api
    assert client.post("/api/auth/demo", json={"role": "admin"}).status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    monkeypatch.setenv("MODE", "CONNECTED")
    get_settings.cache_clear()
    assert client.get("/api/auth/me").status_code == 401
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@arc-field-demo.example.com", "password": "DemoQuote2026!"},
    )
    assert response.status_code == 401


def test_hubspot_adapter_contract_uses_fixed_destination():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200 if "contacts" in request.url.path else 201, json={"id": "deal-42"}
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.hubapi.com")
    connector = HubSpotConnector("test-token", client=client)
    provider_id = connector.upsert_accepted_deal(
        client_email="buyer@example.com", client_name="Buyer", quote_id="quote-1", total="123.45"
    )
    assert provider_id == "deal-42"
    assert [request.url.host for request in requests] == ["api.hubapi.com", "api.hubapi.com"]
    assert all(request.headers["Authorization"] == "Bearer test-token" for request in requests)


def test_rate_limited_connector_backoff_is_bounded(api, monkeypatch):
    _, factory = api
    monkeypatch.setenv("MODE", "CONNECTED")
    monkeypatch.setenv("HUBSPOT_ENABLED", "true")
    monkeypatch.setenv("HUBSPOT_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("WORKER_BACKOFF_SECONDS", "30")
    get_settings.cache_clear()

    class RateLimited:
        def upsert_accepted_deal(self, **kwargs):
            request = httpx.Request("POST", "https://api.hubapi.com/crm/v3/objects/deals")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    with factory() as db:
        brief = db.scalar(select(Brief).where(Brief.workspace_id == "arc-field-demo"))
        quote = Quote(workspace_id=brief.workspace_id, client_id=brief.client_id, brief_id=brief.id)
        db.add(quote)
        db.flush()
        event = OutboxEvent(
            workspace_id=brief.workspace_id,
            event_type="crm.accepted_quote",
            idempotency_key="retry-test",
            payload={"quote_id": quote.id, "total": "123.45"},
        )
        db.add(event)
        db.commit()
        first = process_outbox_once(db, RateLimited())
        assert first["status"] == "pending"
        assert event.attempts == 1
        assert event.next_attempt_at > datetime.now(UTC)
        assert process_outbox_once(db, RateLimited())["processed"] == 0
        event.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        second = process_outbox_once(db, RateLimited())
        assert second["status"] == "failed"
        assert event.attempts == 2
    get_settings.cache_clear()
