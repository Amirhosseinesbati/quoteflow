"""Customer defaults must persist, stay scoped, and never rewrite an approved document."""

from io import BytesIO

import pytest
from pypdf import PdfReader


def login(client, role="admin", workspace="arc-field-demo"):
    assert client.post("/api/auth/demo", json={"role": role, "workspace": workspace}).status_code == 200


def profile(client):
    response = client.get("/api/studio-settings")
    assert response.status_code == 200, response.text
    return response.json()


def ready(client):
    response = client.post("/api/briefs", json={
        "company_name": "Example Client",
        "text": "We need a five-page website and analytics. We can supply final photography and copy. The budget is $20,000 and launch is in twelve weeks.",
    })
    assert response.status_code == 201
    brief_id = response.json()["id"]
    analyzed = client.post(f"/api/briefs/{brief_id}/analyze").json()
    for question in analyzed["clarifications"]:
        assert client.post(f"/api/briefs/{brief_id}/clarifications/{question['id']}/answer", json={"answer": "Twelve weeks; $20,000; final inputs supplied."}).status_code == 200
    options = client.post(f"/api/briefs/{brief_id}/options")
    assert options.status_code == 200, options.text
    return brief_id, options.json()


def test_settings_require_admin_and_remain_workspace_scoped(api):
    client, _ = api
    assert client.get("/api/studio-settings").status_code == 401
    login(client)
    original = profile(client)
    settings = {**original["settings"], "studio_name": "Northstar Studio", "currency": "EUR"}
    saved = client.put("/api/studio-settings", json={"settings": settings, "expected_revision": 0})
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    assert client.put("/api/studio-settings", json={"settings": settings, "expected_revision": 0}).status_code == 409
    for role in ("operator", "viewer"):
        login(client, role)
        assert profile(client)["settings"]["studio_name"] == "Northstar Studio"
        assert client.put("/api/studio-settings", json={"settings": settings, "expected_revision": 1}).status_code == 403
    login(client, workspace="arc-field-isolation")
    assert profile(client)["settings"]["studio_name"] == "Arc & Field Studio"
    assert profile(client)["revision"] == 0
    login(client)
    assert profile(client)["settings"]["currency"] == "EUR"


@pytest.mark.parametrize(("field", "value"), [
    ("currency", "XXX"), ("accent_color", "javascript:alert(1)"), ("studio_name", "  "), ("studio_name", "Studio\n" * 5),
    ("default_tax_percent", "NaN"), ("default_tax_percent", "101"),
    ("default_tax_percent", "-1"), ("default_tax_percent", "2.123"),
    ("default_contingency_percent", "Infinity"), ("approval_discount_threshold", "invalid"),
])
def test_invalid_customer_defaults_are_rejected_without_mutation(api, field, value):
    client, _ = api
    login(client)
    original = profile(client)
    response = client.put("/api/studio-settings", json={
        "settings": {**original["settings"], field: value}, "expected_revision": 0,
    })
    assert response.status_code == 422, response.text
    assert profile(client) == original


def test_brand_currency_terms_policy_and_pdf_are_version_frozen(api):
    client, _ = api
    login(client)
    settings = {**profile(client)["settings"], "studio_name": "Northstar Studio", "currency": "EUR",
        "tax_label": "VAT", "default_tax_percent": "20.00", "default_contingency_percent": "5.00",
        "approval_discount_threshold": "5.00", "title_template": "A clear path for {client}",
        "summary_template": "{studio} prepares a {package} plan for {client}.",
        "terms": "Start conditions: approved statement of work and agreed deposit.",
    }
    assert client.put("/api/studio-settings", json={"settings": settings, "expected_revision": 0}).status_code == 200
    brief_id, options = ready(client)
    quote_id = options["quote_id"]
    version = options["options"][1]
    assert version["proposal"]["_document"]["currency"] == "EUR"
    assert version["tax_percent"] == "20.00"
    assert version["contingency_percent"] == "5.00"
    assert version["proposal"]["terms"] == settings["terms"]
    assert "Northstar Studio prepares a recommended plan for Example Client" in version["proposal"]["executive_summary"]
    changed = {**settings, "studio_name": "Changed Studio", "currency": "GBP", "terms": "Different terms for future options only."}
    assert client.put("/api/studio-settings", json={"settings": changed, "expected_revision": 1}).status_code == 200
    invalid = client.patch(f"/api/quotes/{quote_id}/versions/{version['id']}", json={"proposal": {"_document": {"currency": "GBP"}}})
    assert invalid.status_code == 422
    malformed = client.patch(f"/api/quotes/{quote_id}/versions/{version['id']}", json={"proposal": {"scope": {"bad": "section"}}})
    assert malformed.status_code == 422
    revised = client.patch(f"/api/quotes/{quote_id}/versions/{version['id']}", json={"discount_percent": "6.00"})
    assert revised.status_code == 200, revised.text
    revision = revised.json()
    assert revision["approval_required"]
    assert revision["proposal"]["_document"] == version["proposal"]["_document"]
    url = f"/api/quotes/{quote_id}/versions/{revision['id']}"
    assert client.post(url + "/publish").status_code == 409
    approval = client.post(url + "/submit-review").json()
    assert client.post(f"/api/approvals/{approval['id']}/decision", json={"decision": "approved"}).status_code == 200
    published = client.post(url + "/publish")
    assert published.status_code == 200, published.text
    pdf = client.get(url + "/pdf")
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert "Northstar Studio" in text and "Changed Studio" not in text
    assert "EUR" in text and "GBP" not in text
    assert "VAT (20.00%)" in text and settings["terms"] in text
    portal = client.get("/api/portal/" + published.json()["token"]).json()
    assert portal["quote_version"]["proposal"]["_document"]["currency"] == "EUR"
    regenerated = client.post(f"/api/briefs/{brief_id}/options").json()
    assert regenerated["options"][0]["proposal"]["_document"]["currency"] == "GBP"
    assert regenerated["options"][0]["proposal"]["terms"] == changed["terms"]
    assert client.get("/api/portal/" + published.json()["token"]).status_code == 410


def test_historical_catalog_is_scoped_and_revision_uses_original_rates(api):
    client, _ = api
    login(client)
    _, options = ready(client)
    version = options["options"][0]
    quote_id = options["quote_id"]
    old_catalog = client.get("/api/catalog").json()
    service = old_catalog["services"][0]
    update = {key: value for key, value in service.items() if key != "id"}
    update["base_price"] = "9999.00"
    assert client.patch("/api/catalog/services/" + service["id"], json=update).status_code == 200
    historic = client.get("/api/catalog", params={"version_id": old_catalog["version"]["id"]})
    assert historic.status_code == 200
    assert historic.json() == old_catalog
    revised = client.patch(f"/api/quotes/{quote_id}/versions/{version['id']}", json={"discount_percent": "1.00"})
    assert revised.status_code == 200
    assert revised.json()["subtotal"] == version["subtotal"]
    login(client, workspace="arc-field-isolation")
    assert client.get("/api/catalog", params={"version_id": old_catalog["version"]["id"]}).status_code == 404
