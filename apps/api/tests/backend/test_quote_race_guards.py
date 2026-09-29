"""The quote row is the serialization point for customer and staff decisions."""

from __future__ import annotations

from sqlalchemy import select

from quoteflow.auth import token_digest
from quoteflow.models import CustomerReviewToken, ProjectHandoff, Quote

BRIEF = (
    "We need a five-page responsive website, a lead form, and CRM contact sync. "
    "Our team will supply the approved logo, sitemap, and images. "
    "The launch date and budget can be confirmed during discovery."
)


def _options(client) -> tuple[str, str]:
    login = client.post("/api/auth/demo", json={"role": "operator"})
    assert login.status_code == 200, login.text
    created = client.post(
        "/api/briefs", json={"text": BRIEF, "company_name": "Concurrency Client"}
    )
    assert created.status_code == 201, created.text
    brief_id = created.json()["id"]
    analyzed = client.post(f"/api/briefs/{brief_id}/analyze")
    assert analyzed.status_code == 200, analyzed.text
    for question in analyzed.json()["clarifications"]:
        answered = client.post(
            f"/api/briefs/{brief_id}/clarifications/{question['id']}/answer",
            json={"answer": "Twelve weeks and a $20,000 budget; final assets are supplied."},
        )
        assert answered.status_code == 200, answered.text
    options = client.post(f"/api/briefs/{brief_id}/options")
    assert options.status_code == 200, options.text
    return brief_id, options.json()["options"][0]["id"]


def test_portal_revalidates_token_after_quote_lock(api, monkeypatch):
    client, factory = api
    brief_id, version_id = _options(client)
    quote_id = client.get(f"/api/briefs/{brief_id}").json()["quote_id"]
    published = client.post(f"/api/quotes/{quote_id}/versions/{version_id}/publish")
    assert published.status_code == 200, published.text
    token = published.json()["token"]

    from quoteflow import main

    lock_quote = main._locked_scoped_quote

    def replace_during_lock_wait(db, requested_quote_id, workspace_id):
        quote = lock_quote(db, requested_quote_id, workspace_id)
        record = db.scalar(
            select(CustomerReviewToken).where(
                CustomerReviewToken.token_hash == token_digest(token)
            )
        )
        record.status = "replaced"
        db.commit()  # Simulate a competing request completing during the wait.
        return quote

    monkeypatch.setattr(main, "_locked_scoped_quote", replace_during_lock_wait)
    client.cookies.clear()
    response = client.post(f"/api/portal/{token}/response", json={"decision": "accepted"})
    assert response.status_code == 410, response.text
    with factory() as db:
        assert db.get(Quote, quote_id).status == "published"
        assert db.scalar(
            select(ProjectHandoff).where(ProjectHandoff.quote_version_id == version_id)
        ) is None


def test_revision_requested_quote_cannot_publish_old_price(api):
    client, factory = api
    brief_id, version_id = _options(client)
    quote_id = client.get(f"/api/briefs/{brief_id}").json()["quote_id"]
    with factory() as db:
        quote = db.get(Quote, quote_id)
        quote.status = "revision_requested"
        db.commit()
    blocked = client.post(f"/api/quotes/{quote_id}/versions/{version_id}/publish")
    assert blocked.status_code == 409, blocked.text

    regenerated = client.post(f"/api/briefs/{brief_id}/options")
    assert regenerated.status_code == 200, regenerated.text
    current_id = regenerated.json()["options"][0]["id"]
    published = client.post(f"/api/quotes/{quote_id}/versions/{current_id}/publish")
    assert published.status_code == 200, published.text
