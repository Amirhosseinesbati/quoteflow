"""Customer answers change only the explicitly named catalog scope and quantity."""

from __future__ import annotations

from decimal import Decimal

import pytest

from quoteflow.models import Brief, Clarification, ServiceCatalogEntry
from quoteflow.proposals import estimate_quantity

BRIEF_TEXT = (
    "We need a 5-page responsive website in 12 weeks with a budget of $18,000-$25,000. "
    "We can supply approved photography and a sitemap."
)


def _json(response, status: int = 200):
    assert response.status_code == status, response.text
    return response.json()


def _ready_quote(client):
    _json(client.post("/api/auth/demo", json={"workspace": "arc-field-demo", "role": "operator"}))
    brief = _json(
        client.post(
            "/api/briefs",
            json={"text": BRIEF_TEXT, "company_name": "Scope Check Studio"},
        ),
        201,
    )
    analyzed = _json(client.post(f"/api/briefs/{brief['id']}/analyze"))
    for question in analyzed["clarifications"]:
        _json(
            client.post(
                f"/api/briefs/{brief['id']}/clarifications/{question['id']}/answer",
                json={"answer": "Final content and access will be supplied."},
            )
        )
    options = _json(client.post(f"/api/briefs/{brief['id']}/options"))
    return brief["id"], options


def _customer_answer(client, brief_id: str, question: str, answer: str) -> None:
    item = _json(
        client.post(
            f"/api/briefs/{brief_id}/clarifications", json={"question": question}
        ),
        201,
    )
    token = _json(client.post(f"/api/briefs/{brief_id}/portal-link"))["token"]
    client.cookies.clear()
    _json(
        client.post(
            f"/api/portal/{token}/clarifications/{item['id']}/answer",
            json={"answer": answer},
        )
    )
    _json(client.post("/api/auth/demo", json={"workspace": "arc-field-demo", "role": "operator"}))


def _line(option: dict, code: str) -> dict | None:
    return next((line for line in option["lines"] if line["service_code"] == code), None)


def test_answer_quantity_is_bound_to_its_named_service():
    brief = Brief(source_text="We need a 5-page responsive website.")
    brief.clarifications = [
        Clarification(
            question="Should content migration be included?",
            answer="Include migration of ten approved pages.",
            status="answered",
            affects=["scope", "price"],
        )
    ]
    migration = ServiceCatalogEntry(
        code="web-content", name="Content migration", unit="page"
    )
    design = ServiceCatalogEntry(
        code="web-design", name="Responsive page design", unit="page"
    )

    assert estimate_quantity(brief, migration) == "10"
    assert estimate_quantity(brief, design) == "5"


def test_explicit_customer_page_count_reprices_only_named_service(api):
    client, _ = api
    brief_id, original = _ready_quote(client)
    original_design = next(
        _line(option, "web-design") for option in original["options"] if _line(option, "web-design")
    )
    assert Decimal(original_design["quantity"]) == 5

    _customer_answer(
        client,
        brief_id,
        "How many responsive page designs should the scope include?",
        "Include 8 pages of responsive design.",
    )
    regenerated = _json(client.post(f"/api/briefs/{brief_id}/options"))
    revised_design = next(
        _line(option, "web-design")
        for option in regenerated["options"]
        if _line(option, "web-design")
    )
    assert Decimal(revised_design["quantity"]) == 8
    assert Decimal(revised_design["line_total"]) == 8 * Decimal(revised_design["unit_price"])
    assert revised_design["line_total"] != original_design["line_total"]
    for option in regenerated["options"]:
        website_build = _line(option, "web-build")
        if website_build:
            assert Decimal(website_build["quantity"]) == 5


def test_explicit_customer_scope_addition_enters_regenerated_options(api):
    client, _ = api
    brief_id, original = _ready_quote(client)
    assert _line(original["options"][0], "intake-crm") is None

    _customer_answer(
        client,
        brief_id,
        "Should the scope include CRM contact sync?",
        "Include CRM contact sync.",
    )
    regenerated = _json(client.post(f"/api/briefs/{brief_id}/options"))
    assert any(_line(option, "intake-crm") for option in regenerated["options"])
    assert any(
        "CRM contact sync" in option["proposal"]["scope"]
        for option in regenerated["options"]
    )
    quote = _json(client.get(f"/api/quotes/{original['quote_id']}"))
    original_ids = {option["id"] for option in original["options"]}
    assert all(
        version["status"] == "superseded"
        for version in quote["versions"]
        if version["id"] in original_ids
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Maybe include CRM contact sync later.",
        "Do not include CRM contact sync.",
        "We want to explore CRM contact sync before committing.",
    ],
)
def test_vague_or_negative_answer_does_not_add_binding_scope(api, answer):
    client, _ = api
    brief_id, original = _ready_quote(client)
    original_codes = [
        [line["service_code"] for line in option["lines"]]
        for option in original["options"]
    ]

    _customer_answer(client, brief_id, "Should the scope include CRM contact sync?", answer)
    regenerated = _json(client.post(f"/api/briefs/{brief_id}/options"))
    new_codes = [
        [line["service_code"] for line in option["lines"]]
        for option in regenerated["options"]
    ]
    assert new_codes == original_codes
