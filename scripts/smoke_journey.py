"""Run the DEMO quote journey against a local API without sending external messages."""

from __future__ import annotations

import io
import os
import sys
from decimal import Decimal

import httpx
from pypdf import PdfReader


BASE = os.environ.get("QUOTEFLOW_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API = BASE + "/api"


def call(client: httpx.Client, method: str, path: str, *, expected: int = 200, **kwargs):
    response = client.request(method, API + path, **kwargs)
    if response.status_code != expected:
        raise AssertionError(f"{method} {path}: expected {expected}, got {response.status_code}: {response.text[:700]}")
    return response.json() if response.content and "json" in response.headers.get("content-type", "") else response


def main() -> None:
    with httpx.Client(timeout=60.0, follow_redirects=False) as operator, \
         httpx.Client(timeout=60.0, follow_redirects=False) as admin, \
         httpx.Client(timeout=60.0, follow_redirects=False) as outsider:
        call(operator, "POST", "/auth/demo", json={"workspace": "arc-field-demo", "role": "operator"})
        call(admin, "POST", "/auth/demo", json={"workspace": "arc-field-demo", "role": "admin"})
        call(outsider, "POST", "/auth/demo", json={"workspace": "arc-field-isolation", "role": "viewer"})
        brief = call(operator, "POST", "/briefs", expected=201, json={
            "source_type": "paste",
            "company_name": "Smoke Example Studio",
            "contact_name": "Morgan Test",
            "contact_email": "morgan@smoke-example.test",
            "text": ("Smoke Example Studio needs a five-page responsive website, analytics, and a CRM contact sync "
                     "in twelve weeks. Our working budget is $18,000–$30,000. We can supply approved "
                     "photography and a draft sitemap. We need a clear content owner and two review rounds. "
                     "Please address Morgan Test at morgan@smoke-example.test."),
        })
        brief_id = brief["id"]
        call(outsider, "GET", f"/briefs/{brief_id}", expected=404)
        analyzed = call(operator, "POST", f"/briefs/{brief_id}/analyze")
        clarifications = analyzed.get("clarifications", [])
        if len(clarifications) < 2:
            for question in ("Who will approve the final content?", "Which CRM environment is available for testing?"):
                clarifications.append(call(operator, "POST", f"/briefs/{brief_id}/clarifications", expected=201,
                                           json={"question": question}))
        for index, item in enumerate(clarifications[:2]):
            call(operator, "POST", f"/briefs/{brief_id}/clarifications/{item['id']}/answer",
                 json={"answer": ["Morgan will approve final content.", "A sandbox CRM is available."][index]})
        result = call(operator, "POST", f"/briefs/{brief_id}/options")
        options = result["options"]
        assert len(options) == 3, f"Expected 3 scope options, got {len(options)}"
        assert len({item["total"] for item in options}) >= 2, "Scope options have identical prices"
        quote_id = result["quote_id"]
        call(outsider, "GET", f"/quotes/{quote_id}", expected=404)
        selected = options[1]
        preview = call(operator, "POST", f"/quotes/{quote_id}/versions/{selected['id']}/price-preview",
                       json={"discount_percent": "15.00"})
        assert Decimal(preview["total"]) < Decimal(selected["total"])
        changed = call(operator, "PATCH", f"/quotes/{quote_id}/versions/{selected['id']}",
                       json={"discount_percent": "15.00"})
        assert changed["id"] != selected["id"], "Price edit did not create a replacement version"
        version_id = changed["id"]
        diff = call(operator, "GET", f"/quotes/{quote_id}/diff?from={selected['id']}&to={version_id}")
        assert Decimal(diff["total_delta"]) < 0, "Scope/price diff did not capture discount"
        approval = call(operator, "POST", f"/quotes/{quote_id}/versions/{version_id}/submit-review")
        assert approval["status"] == "pending"
        call(operator, "POST", f"/quotes/{quote_id}/versions/{version_id}/publish", expected=409)
        decided = call(admin, "POST", f"/approvals/{approval['id']}/decision", json={"decision": "approved"})
        assert decided["status"] == "approved"
        published = call(operator, "POST", f"/quotes/{quote_id}/versions/{version_id}/publish")
        token = published["token"]
        pdf = operator.get(API + f"/quotes/{quote_id}/versions/{version_id}/pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-"), "PDF download failed"
        pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf.content)).pages)
        assert "Smoke Example Studio" in pdf_text, "PDF client name mismatch"
        assert str(Decimal(changed["total"])) in pdf_text or f"{Decimal(changed['total']):,.2f}" in pdf_text, "PDF total mismatch"
        portal = call(httpx.Client(timeout=60.0), "GET", f"/portal/{token}")
        assert portal["kind"] == "review"
        call(operator, "GET", f"/portal/{token}modified", expected=404)
        response = call(operator, "POST", f"/portal/{token}/response", json={"decision": "accepted"})
        again = call(operator, "POST", f"/portal/{token}/response", json={"decision": "accepted"})
        assert response["handoff_id"] == again["handoff_id"]
        handoffs = call(operator, "GET", "/handoffs")["items"]
        assert sum(item["quote_version_id"] == version_id for item in handoffs) == 1
        call(operator, "PATCH", f"/quotes/{quote_id}/versions/{version_id}",
             expected=409, json={"discount_percent": "9.00"})
        old_cookie = outsider.cookies.get("quoteflow_session")
        call(outsider, "POST", "/auth/logout")
        if old_cookie:
            with httpx.Client(timeout=30.0) as replay:
                replay.cookies.set("quoteflow_session", old_cookie)
                call(replay, "GET", "/auth/me", expected=401)
        print({"status": "passed", "brief_id": brief_id, "quote_id": quote_id,
               "version_id": version_id, "total": changed["total"], "pdf_bytes": len(pdf.content),
               "handoff_id": response["handoff_id"]})


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError) as exc:
        print(f"SMOKE FAILURE: {exc}", file=sys.stderr)
        raise SystemExit(1)
