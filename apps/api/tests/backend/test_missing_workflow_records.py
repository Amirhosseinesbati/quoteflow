"""A removed proposal must fail actionably before publishing or accepting it."""

import pytest

from quoteflow import workflow


@pytest.mark.parametrize("action", ["_validate_proposal", "_internal_review", "_render_version", "_customer_response"])
def test_missing_workflow_records_return_actionable_error(api, monkeypatch, action):
    _, factory = api
    monkeypatch.setattr(workflow, "SessionLocal", factory)
    monkeypatch.setattr(workflow, "interrupt", lambda _: "missing-version")
    state = {"option_ids": ["missing-version"], "selected_version_id": "missing-version", "quote_id": "missing-quote"}
    with pytest.raises(ValueError, match="unavailable"):
        getattr(workflow, action)(state)
