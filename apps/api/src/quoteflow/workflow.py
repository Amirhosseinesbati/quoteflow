"""Recoverable QuoteFlow StateGraph around persisted application use cases."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from fastapi import HTTPException
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .models import Approval, Job, ProjectHandoff, ProposalAsset, Quote, QuoteVersion
from .pricing import calculate
from .services import (
    analyze_brief,
    catalog_entries,
    generate_options,
    get_scoped_brief,
    latest_catalog,
    record_clarification_answer,
)


class QuoteFlowState(TypedDict, total=False):
    run_id: str
    workspace_id: str
    brief_id: str
    quote_id: str
    option_ids: list[str]
    selected_version_id: str
    open_questions: list[dict]
    answers: dict[str, str]
    catalog_version_id: str
    matched_service_ids: list[str]
    pricing_valid: bool
    response_status: str
    handoff_id: str
    attempts: int


class WorkflowCancelled(Exception):
    pass


def _guard(state: QuoteFlowState) -> None:
    run_id = state.get("run_id")
    if not run_id:
        return
    with SessionLocal() as db:
        job = db.get(Job, run_id)
        if job is None or job.workspace_id != state["workspace_id"]:
            raise ValueError("Workflow run is outside the requested workspace")
        if job.status in ("cancel_requested", "cancelled"):
            raise WorkflowCancelled("Workflow cancellation requested")


def _intake(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        get_scoped_brief(db, state["brief_id"], state["workspace_id"])
    return {"attempts": state.get("attempts", 0)}


def _extract(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        brief = get_scoped_brief(db, state["brief_id"], state["workspace_id"])
        if not brief.extracted:
            analyze_brief(db, brief)
    return {}


def _assess_missing(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        brief = get_scoped_brief(db, state["brief_id"], state["workspace_id"])
        questions = [
            {"id": item.id, "question": item.question}
            for item in brief.clarifications
            if item.status == "open"
        ]
    return {"open_questions": questions}


def _clarification(state: QuoteFlowState) -> dict:
    answers = interrupt(
        {
            "kind": "clarification",
            "brief_id": state["brief_id"],
            "questions": state.get("open_questions", []),
        }
    )
    if not isinstance(answers, Mapping):
        raise ValueError("Clarification resume value must map question IDs to answers")
    return {"answers": dict(answers)}


def _save_clarification(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        brief = get_scoped_brief(db, state["brief_id"], state["workspace_id"])
        valid_ids = {item.id for item in brief.clarifications}
        for key, answer in state.get("answers", {}).items():
            if key not in valid_ids:
                raise HTTPException(403, "Clarification is outside this brief")
            item = next(item for item in brief.clarifications if item.id == key)
            record_clarification_answer(db, item, str(answer))
    return {"answers": {}}


def _match_catalog(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        version = latest_catalog(db, state["workspace_id"])
        services = catalog_entries(db, version.id)
        if len([item for item in services if item.active]) < 6:
            raise ValueError("At least six active catalog services are required for three options")
    return {"catalog_version_id": version.id}


def _draft_scope(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        brief = get_scoped_brief(db, state["brief_id"], state["workspace_id"])
        quote = db.scalar(select(Quote).where(Quote.brief_id == brief.id))
        if quote and quote.status == "options_ready":
            options = [version for version in quote.versions if version.status == "draft"]
            if len(options) == 3:
                return {"quote_id": quote.id, "option_ids": [version.id for version in options]}
        generated = generate_options(db, brief)
        return {
            "quote_id": generated["quote_id"],
            "option_ids": [item["id"] for item in generated["options"]],
        }


def _compute_price(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        for version_id in state["option_ids"]:
            version = db.get(QuoteVersion, version_id)
            if version is None or version.quote_id != state["quote_id"]:
                raise ValueError("Quote option unavailable")
            lines = [
                {"quantity": str(item.quantity), "unit_price": str(item.unit_price)}
                for item in version.lines
            ]
            priced = calculate(
                lines,
                discount_percent=str(version.discount_percent),
                tax_percent=str(version.tax_percent),
                contingency_percent=str(version.contingency_percent),
            )
            if priced["total"] != str(version.total):
                raise ValueError("Persisted price disagrees with deterministic calculation")
    return {"pricing_valid": True}


def _validate_proposal(state: QuoteFlowState) -> dict:
    required = {
        "executive_summary",
        "objectives",
        "scope",
        "deliverables",
        "exclusions",
        "assumptions",
        "schedule",
        "milestones",
        "client_responsibilities",
        "acceptance_steps",
    }
    with SessionLocal() as db:
        for version_id in state["option_ids"]:
            version = db.get(QuoteVersion, version_id)
            if version is None:
                raise ValueError("Proposal version is unavailable")
            if not required.issubset(version.proposal):
                raise ValueError("Proposal is missing a required section")
    return {}


def _internal_review(state: QuoteFlowState) -> dict:
    selected = interrupt(
        {
            "kind": "internal_review",
            "quote_id": state["quote_id"],
            "option_ids": state["option_ids"],
        }
    )
    if not isinstance(selected, str) or selected not in state["option_ids"]:
        raise ValueError("Choose one of the generated option IDs")
    with SessionLocal() as db:
        version = db.get(QuoteVersion, selected)
        if version is None:
            raise ValueError("Selected proposal version is unavailable")
        approval = db.scalar(
            select(Approval).where(
                Approval.quote_version_id == selected, Approval.content_hash == version.content_hash
            )
        )
        if version.approval_required and (approval is None or approval.status != "approved"):
            raise ValueError("Selected option still needs approval")
    return {"selected_version_id": selected}


def _render_version(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        version = db.get(QuoteVersion, state["selected_version_id"])
        if version is None:
            raise ValueError("Selected proposal version is unavailable")
        asset = db.scalar(select(ProposalAsset).where(ProposalAsset.quote_version_id == version.id))
        if version.status in ("published", "accepted") and asset is not None:
            return {}
    interrupt(
        {
            "kind": "publish_required",
            "quote_id": state["quote_id"],
            "version_id": state["selected_version_id"],
        }
    )
    with SessionLocal() as db:
        version = db.get(QuoteVersion, state["selected_version_id"])
        if version is None:
            raise ValueError("Selected proposal version is unavailable")
        asset = db.scalar(select(ProposalAsset).where(ProposalAsset.quote_version_id == version.id))
        if version.status not in ("published", "accepted") or asset is None:
            raise ValueError("Selected option has not been published")
    return {}


def _customer_response(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        quote = db.get(Quote, state["quote_id"])
        if quote is None:
            raise ValueError("Proposal quote is unavailable")
        if quote.status == "accepted":
            return {"response_status": "accepted"}
        if quote.status in ("declined", "revision_requested"):
            return {"response_status": quote.status}
    interrupt(
        {
            "kind": "customer_review",
            "quote_id": state["quote_id"],
            "version_id": state["selected_version_id"],
        }
    )
    with SessionLocal() as db:
        quote = db.get(Quote, state["quote_id"])
        if quote is None:
            raise ValueError("Proposal quote is unavailable")
        return {"response_status": quote.status}


def _project_handoff(state: QuoteFlowState) -> dict:
    with SessionLocal() as db:
        record = db.scalar(
            select(ProjectHandoff).where(
                ProjectHandoff.quote_version_id == state["selected_version_id"],
                ProjectHandoff.workspace_id == state["workspace_id"],
            )
        )
        if record is None:
            raise ValueError("Accepted quote has no local handoff")
        return {"handoff_id": record.id}


def build_workflow(checkpointer):
    graph = StateGraph(QuoteFlowState)

    def guard_action(action):
        def guarded(state: QuoteFlowState):
            _guard(state)
            return action(state)

        return guarded

    for name, node in (
        ("intake", _intake),
        ("extract_brief", _extract),
        ("assess_missing", _assess_missing),
        ("clarification", _clarification),
        ("save_clarification", _save_clarification),
        ("match_catalog", _match_catalog),
        ("draft_scope", _draft_scope),
        ("compute_price", _compute_price),
        ("validate_proposal", _validate_proposal),
        ("internal_review", _internal_review),
        ("render_version", _render_version),
        ("customer_response", _customer_response),
        ("project_handoff", _project_handoff),
    ):
        graph.add_node(name, guard_action(node))
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "extract_brief")
    graph.add_edge("extract_brief", "assess_missing")
    graph.add_conditional_edges(
        "assess_missing",
        lambda state: "clarification" if state.get("open_questions") else "match_catalog",
        ["clarification", "match_catalog"],
    )
    graph.add_edge("clarification", "save_clarification")
    graph.add_edge("save_clarification", "assess_missing")
    for before, after in (
        ("match_catalog", "draft_scope"),
        ("draft_scope", "compute_price"),
        ("compute_price", "validate_proposal"),
        ("validate_proposal", "internal_review"),
        ("internal_review", "render_version"),
        ("render_version", "customer_response"),
    ):
        graph.add_edge(before, after)
    graph.add_conditional_edges(
        "customer_response",
        lambda state: "project_handoff" if state.get("response_status") == "accepted" else END,
        ["project_handoff", END],
    )
    graph.add_edge("project_handoff", END)
    return graph.compile(checkpointer=checkpointer)


def make_checkpointer():
    url = get_settings().database_url
    if not url.startswith("postgresql"):
        return InMemorySaver(), None
    from langgraph.checkpoint.postgres import PostgresSaver

    manager = PostgresSaver.from_conn_string(url.replace("postgresql+psycopg://", "postgresql://"))
    try:
        checkpointer = manager.__enter__()
        checkpointer.setup()
    except BaseException as exc:
        with suppress(Exception):
            manager.__exit__(type(exc), exc, exc.__traceback__)
        raise
    return checkpointer, manager


def invoke_job(graph, db, job: Job, resume: object | None = None, *, recover: bool = False) -> dict:
    config = {"configurable": {"thread_id": job.id}, "recursion_limit": 30}
    job.lease_until = datetime.now(UTC) + timedelta(minutes=5)
    db.commit()
    try:
        result = graph.invoke(
            Command(resume=resume)
            if resume is not None
            else None
            if recover
            else {
                "run_id": job.id,
                "workspace_id": job.workspace_id,
                "brief_id": job.payload["brief_id"],
                "attempts": 0,
            },
            config,
        )
    except WorkflowCancelled:
        db.refresh(job)
        job.status = "cancelled"
        job.lease_until = None
        db.commit()
        return {"id": job.id, "status": "cancelled", "progress": job.progress}
    except Exception as exc:
        db.refresh(job)
        job.status = "failed"
        job.failure_reason = f"{type(exc).__name__}: {exc}"[:1000]
        job.lease_until = None
        db.commit()
        raise
    db.refresh(job)
    if job.status == "cancel_requested":
        job.status = "cancelled"
        job.lease_until = None
        db.commit()
        return {"id": job.id, "status": "cancelled", "progress": job.progress}
    job_payload = dict(job.payload)
    if result.get("quote_id"):
        job_payload["quote_id"] = result["quote_id"]
    interrupts = result.get("__interrupt__", [])
    if interrupts:
        interrupt_value = interrupts[0].value
        kind = (
            interrupt_value.get("kind", "unknown")
            if isinstance(interrupt_value, dict)
            else "unknown"
        )
        job.status = f"waiting_{kind}"
        job.progress = {
            "clarification": 20,
            "internal_review": 65,
            "publish_required": 75,
            "customer_review": 90,
        }.get(kind, 50)
        job_payload["waiting_kind"] = kind
        job.payload = job_payload
        job.lease_until = None
        db.commit()
        return {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "interrupt": interrupt_value,
            "quote_id": job_payload.get("quote_id"),
        }
    job.status = "completed"
    job.progress = 100
    job_payload["handoff_id"] = result.get("handoff_id")
    job.payload = job_payload
    job.lease_until = None
    db.commit()
    return {
        "id": job.id,
        "status": job.status,
        "progress": 100,
        "handoff_id": result.get("handoff_id"),
        "quote_id": result.get("quote_id"),
    }


def recover_expired_jobs(graph, db) -> list[dict]:
    expired = db.scalars(
        select(Job).where(
            Job.status.in_(("running", "cancel_requested")), Job.lease_until < datetime.now(UTC)
        )
    ).all()
    results = []
    for job in expired:
        if job.status == "cancel_requested":
            job.status = "cancelled"
            job.lease_until = None
            results.append({"id": job.id, "status": "cancelled"})
            continue
        try:
            results.append(invoke_job(graph, db, job, recover=True))
        except Exception:
            # invoke_job persists the concrete failure reason on the job.
            results.append({"id": job.id, "status": "failed", "reason": job.failure_reason})
    db.commit()
    return results
