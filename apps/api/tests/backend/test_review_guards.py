"""Integration checks for customer scope changes and version-bound review links."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from quoteflow.auth import token_digest
from quoteflow.models import Approval, BriefRevision, CustomerReviewToken, Quote

BRIEF_TEXT = (
    "We need a five-page responsive website, a lead form, and CRM contact sync. "
    "We can supply a draft sitemap and approved images. "
    "Our launch date and budget are still open."
)


def _json(response, status: int = 200):
    assert response.status_code == status, response.text
    return response.json()


def _login(client, role: str = "operator") -> None:
    _json(client.post("/api/auth/demo", json={"workspace": "arc-field-demo", "role": role}))


def _create_brief(client, company: str = "Morrow Pantry") -> str:
    brief = _json(
        client.post(
            "/api/briefs",
            json={
                "text": BRIEF_TEXT,
                "company_name": company,
                "contact_name": "Avery Lee",
                "contact_email": "avery@example.com",
            },
        ),
        201,
    )
    return brief["id"]


def _ready_quote(client):
    brief_id = _create_brief(client)
    analyzed = _json(client.post(f"/api/briefs/{brief_id}/analyze"))
    for question in analyzed["clarifications"]:
        _json(
            client.post(
                f"/api/briefs/{brief_id}/clarifications/{question['id']}/answer",
                json={"answer": "Twelve weeks; $20,000-$30,000; final content supplied."},
            )
        )
    options = _json(client.post(f"/api/briefs/{brief_id}/options"))
    return brief_id, options["quote_id"], options["options"]


def test_customer_clarification_is_scoped_and_regenerates_options(api):
    client, factory = api
    _login(client)
    brief_id, quote_id, original_options = _ready_quote(client)
    question = _json(
        client.post(
            f"/api/briefs/{brief_id}/clarifications",
            json={"question": "Should the scope include content migration?"},
        ),
        201,
    )
    other_brief = _create_brief(client, "Other Client")
    other_question = _json(
        client.post(
            f"/api/briefs/{other_brief}/clarifications",
            json={"question": "Which launch date is required?"},
        ),
        201,
    )
    token = _json(client.post(f"/api/briefs/{brief_id}/portal-link"))["token"]
    client.cookies.clear()  # Customer links are usable without a staff session.
    assert (
        client.post(
            f"/api/portal/{token}/clarifications/{other_question['id']}/answer",
            json={"answer": "A date from the other client"},
        ).status_code
        == 404
    )

    answer = "Include migration of ten approved pages."
    answered = _json(
        client.post(
            f"/api/portal/{token}/clarifications/{question['id']}/answer",
            json={"answer": answer},
        )
    )
    assert answered["answer"] == answer
    _login(client)
    revised_brief = _json(client.get(f"/api/briefs/{brief_id}"))
    assert revised_brief["extracted"]["clarification_answers"][question["id"]] == answer
    with factory() as db:
        revision = db.scalar(
            select(BriefRevision).where(
                BriefRevision.brief_id == brief_id,
                BriefRevision.number == revised_brief["revision_number"],
            )
        )
        assert revision is not None
        assert revision.extracted["clarification_answers"][question["id"]] == answer
        assert db.get(Quote, quote_id).status == "revision_requested"

    regenerated = _json(client.post(f"/api/briefs/{brief_id}/options"))
    assert regenerated["quote_id"] == quote_id
    assert len(regenerated["options"]) == 3
    original_ids = {item["id"] for item in original_options}
    assert all(option["id"] not in original_ids for option in regenerated["options"])
    assert all(
        any(answer in assumption for assumption in option["proposal"]["assumptions"])
        for option in regenerated["options"]
    )
    quote = _json(client.get(f"/api/quotes/{quote_id}"))
    assert all(
        version["status"] == "superseded"
        for version in quote["versions"]
        if version["id"] in original_ids
    )


def test_expired_replaced_and_stale_portal_links_cannot_accept_new_version(api):
    client, factory = api
    _login(client)
    _, quote_id, options = _ready_quote(client)
    original = options[0]
    old_token = _json(
        client.post(f"/api/quotes/{quote_id}/versions/{original['id']}/publish")
    )["token"]
    with factory() as db:
        record = db.scalar(
            select(CustomerReviewToken).where(
                CustomerReviewToken.token_hash == token_digest(old_token)
            )
        )
        record.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    client.cookies.clear()
    assert (
        client.post(f"/api/portal/{old_token}/response", json={"decision": "accepted"}).status_code
        == 410
    )

    with factory() as db:
        record = db.scalar(
            select(CustomerReviewToken).where(
                CustomerReviewToken.token_hash == token_digest(old_token)
            )
        )
        record.expires_at = datetime.now(UTC) + timedelta(days=1)
        db.commit()
    _login(client)
    replacement = _json(
        client.patch(
            f"/api/quotes/{quote_id}/versions/{original['id']}",
            json={"discount_percent": "1.00"},
        )
    )
    _json(client.post(f"/api/quotes/{quote_id}/versions/{replacement['id']}/publish"))
    client.cookies.clear()
    assert (
        client.post(f"/api/portal/{old_token}/response", json={"decision": "accepted"}).status_code
        == 410
    )

    # Even a legacy active record must fail after its quote version is superseded.
    with factory() as db:
        record = db.scalar(
            select(CustomerReviewToken).where(
                CustomerReviewToken.token_hash == token_digest(old_token)
            )
        )
        record.status = "active"
        db.commit()
    assert (
        client.post(f"/api/portal/{old_token}/response", json={"decision": "accepted"}).status_code
        == 410
    )
    _login(client)
    quote = _json(client.get(f"/api/quotes/{quote_id}"))
    assert quote["accepted_version_id"] is None
    assert quote["status"] == "published"
    current = next(v for v in quote["versions"] if v["id"] == replacement["id"])
    assert current["status"] == "published"


@pytest.mark.parametrize(
    "change",
    [
        {"discount_percent": "16.00"},
        {"proposal": {"scope": "Revised scope includes a client workshop."}},
    ],
    ids=["price", "scope"],
)
def test_price_or_scope_change_requires_fresh_approval(api, change):
    client, factory = api
    _login(client)
    _, quote_id, options = _ready_quote(client)
    reviewed = _json(
        client.patch(
            f"/api/quotes/{quote_id}/versions/{options[0]['id']}",
            json={"discount_percent": "15.00"},
        )
    )
    approval = _json(
        client.post(f"/api/quotes/{quote_id}/versions/{reviewed['id']}/submit-review")
    )
    _login(client, "admin")
    _json(client.post(f"/api/approvals/{approval['id']}/decision", json={"decision": "approved"}))
    _login(client)

    changed = _json(
        client.patch(f"/api/quotes/{quote_id}/versions/{reviewed['id']}", json=change)
    )
    assert changed["source_version_id"] == reviewed["id"]
    assert changed["content_hash"] != reviewed["content_hash"]
    assert changed["approval_required"] is True
    assert changed["approved"] is False
    changed_publish = client.post(f"/api/quotes/{quote_id}/versions/{changed['id']}/publish")
    prior_publish = client.post(f"/api/quotes/{quote_id}/versions/{reviewed['id']}/publish")
    assert changed_publish.status_code == 409
    assert prior_publish.status_code == 409
    with factory() as db:
        prior_approval = db.get(Approval, approval["id"])
        assert prior_approval.status == "approved"
        assert prior_approval.quote_version_id == reviewed["id"]
