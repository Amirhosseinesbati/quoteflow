"""Starting a brief again must find its own active run, even after another brief starts."""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import select

from quoteflow.main import app
from quoteflow.models import Job
from quoteflow.workflow import build_workflow

BRIEF = (
    "We need a responsive website and a CRM form. "
    "Our team can supply a logo and product images. "
    "The budget and launch date have not been settled."
)


def test_start_reuses_matching_active_job_across_other_briefs(api, monkeypatch):
    client, factory = api
    monkeypatch.setattr("quoteflow.workflow.SessionLocal", factory)
    app.state.quote_workflow = build_workflow(InMemorySaver())
    login = client.post("/api/auth/demo", json={"role": "operator"})
    assert login.status_code == 200, login.text

    brief_ids = []
    for company in ("First Client", "Second Client"):
        created = client.post("/api/briefs", json={"text": BRIEF, "company_name": company})
        assert created.status_code == 201, created.text
        brief_ids.append(created.json()["id"])

    first = client.post(f"/api/workflows/briefs/{brief_ids[0]}/start")
    second = client.post(f"/api/workflows/briefs/{brief_ids[1]}/start")
    repeated = client.post(f"/api/workflows/briefs/{brief_ids[0]}/start")
    assert first.status_code == second.status_code == repeated.status_code == 201
    assert first.json()["status"] == second.json()["status"] == "waiting_clarification"
    assert first.json()["id"] != second.json()["id"]
    assert repeated.json()["id"] == first.json()["id"]
    with factory() as db:
        jobs = db.scalars(select(Job).where(Job.kind == "quote_flow")).all()
        assert len(jobs) == 2
