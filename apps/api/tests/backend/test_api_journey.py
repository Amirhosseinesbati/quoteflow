from io import BytesIO

from pypdf import PdfReader
from sqlalchemy import select

from quoteflow.models import ProjectHandoff

BRIEF = (
    "We need a five-page responsive website, a lead form, and CRM contact sync. "
    "We can supply a draft sitemap and approved images. "
    "Our launch date and budget are still open."
)


def auth(client, role="operator", workspace="arc-field-demo"):
    response = client.post("/api/auth/demo", json={"workspace": workspace, "role": role})
    assert response.status_code == 200, response.text


def test_complete_quote_journey_pdf_fidelity_and_idempotent_acceptance(api):
    client, factory = api
    auth(client)
    created = client.post(
        "/api/briefs",
        json={
            "text": BRIEF,
            "company_name": "Morrow Pantry",
            "contact_name": "Avery Lee",
            "contact_email": "avery@morrow.example.com",
        },
    )
    assert created.status_code == 201, created.text
    brief_id = created.json()["id"]
    analyzed = client.post(f"/api/briefs/{brief_id}/analyze")
    assert analyzed.status_code == 200, analyzed.text
    requirements = analyzed.json()["requirements"]
    assert requirements and all(BRIEF[r["start"] : r["end"]] == r["evidence"] for r in requirements)
    for question in analyzed.json()["clarifications"]:
        answered = client.post(
            f"/api/briefs/{brief_id}/clarifications/{question['id']}/answer",
            json={"answer": "Twelve weeks; $20,000-$30,000, final content supplied."},
        )
        assert answered.status_code == 200, answered.text
    options = client.post(f"/api/briefs/{brief_id}/options")
    assert options.status_code == 200, options.text
    quote_id = options.json()["quote_id"]
    versions = options.json()["options"]
    assert len(versions) == 3
    assert len({version["total"] for version in versions}) == 3
    selected = versions[0]
    revised = client.patch(
        f"/api/quotes/{quote_id}/versions/{selected['id']}", json={"discount_percent": "15.00"}
    )
    assert revised.status_code == 200, revised.text
    version = revised.json()
    assert version["source_version_id"] == selected["id"]
    assert version["approval_required"] is True
    gated = client.post(f"/api/quotes/{quote_id}/versions/{version['id']}/publish")
    assert gated.status_code == 409
    request = client.post(f"/api/quotes/{quote_id}/versions/{version['id']}/submit-review")
    assert request.status_code == 200, request.text
    approval_id = request.json()["id"]
    auth(client, "admin")
    decision = client.post(f"/api/approvals/{approval_id}/decision", json={"decision": "approved"})
    assert decision.status_code == 200, decision.text
    auth(client, "operator")
    published = client.post(f"/api/quotes/{quote_id}/versions/{version['id']}/publish")
    assert published.status_code == 200, published.text
    pdf = client.get(f"/api/quotes/{quote_id}/versions/{version['id']}/pdf")
    assert pdf.status_code == 200
    pdf_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert "Morrow Pantry" in pdf_text
    assert str(version["total"]) in pdf_text.replace(",", "")
    assert version["catalog_version_id"] in pdf_text
    assert version["content_hash"][:10] in pdf_text
    token = published.json()["token"]
    portal = client.get(f"/api/portal/{token}")
    assert portal.status_code == 200
    assert portal.json()["quote_version"]["id"] == version["id"]
    accepted = client.post(f"/api/portal/{token}/response", json={"decision": "accepted"})
    assert accepted.status_code == 200, accepted.text
    repeated = client.post(f"/api/portal/{token}/response", json={"decision": "accepted"})
    assert repeated.status_code == 200
    assert repeated.json()["handoff_id"] == accepted.json()["handoff_id"]
    with factory() as db:
        assert (
            len(
                db.scalars(
                    select(ProjectHandoff).where(ProjectHandoff.quote_version_id == version["id"])
                ).all()
            )
            == 1
        )
    mutation = client.patch(
        f"/api/quotes/{quote_id}/versions/{version['id']}", json={"discount_percent": "0"}
    )
    assert mutation.status_code == 409


def test_workspace_boundary_logout_and_roles(api):
    client, _ = api
    auth(client, "operator")
    brief_id = client.get("/api/briefs").json()["items"][0]["id"]
    cookie = client.cookies.get("quoteflow_session")
    auth(client, "operator", "arc-field-isolation")
    assert client.get(f"/api/briefs/{brief_id}").status_code == 404
    auth(client, "viewer")
    assert client.post(f"/api/briefs/{brief_id}/analyze").status_code == 403
    auth(client, "operator")
    live_cookie = client.cookies.get("quoteflow_session")
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("quoteflow_session", live_cookie)
    assert client.get("/api/auth/me").status_code == 401
    assert cookie != live_cookie
