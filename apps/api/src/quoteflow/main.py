"""QuoteFlow HTTP application."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pypdf import PdfReader
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .access_log import install_access_log_redaction
from .auth import (
    COOKIE_NAME,
    current_user,
    demo_user,
    issue_session,
    login,
    require_role,
    token_digest,
)
from .config import get_settings
from .db import Base, engine, get_db
from .integrations import record_local_handoff
from .models import (
    Approval,
    Brief,
    BriefRevision,
    Clarification,
    Client,
    CustomerReviewToken,
    Job,
    OutboxEvent,
    ProjectHandoff,
    ProposalAsset,
    Quote,
    QuoteVersion,
    ServiceCatalogEntry,
    ServiceCatalogVersion,
    SessionRecord,
    User,
    WorkspacePreference,
    now,
)
from .pdf import render_proposal_pdf
from .pricing import PricingError, decimal
from .schemas import (
    Answer,
    BriefCreate,
    ClarificationCreate,
    ClarificationEdit,
    Decision,
    DemoLogin,
    Login,
    PortalDecision,
    ServiceEdit,
    VersionEdit,
)
from .seed import seed_demo
from .services import (
    analyze_brief,
    catalog_entries,
    generate_options,
    get_scoped_brief,
    get_scoped_quote,
    get_scoped_version,
    issue_portal_token,
    latest_catalog,
    portal_record,
    preview_version,
    record_clarification_answer,
    replace_version,
    serialize_brief,
    serialize_clarification,
    serialize_quote,
    serialize_version,
    timestamp,
)
from .studio import StudioUpdate, document_settings, studio_settings
from .workflow import build_workflow, invoke_job, make_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI):
    install_access_log_redaction()
    settings = get_settings()
    if settings.mode.upper() == "DEMO" and settings.demo_seed:
        Base.metadata.create_all(engine)
        from .db import SessionLocal

        with SessionLocal() as db:
            seed_demo(db, full=False)
    checkpointer, manager = make_checkpointer()
    app.state.quote_workflow = build_workflow(checkpointer)
    yield
    if manager is not None:
        manager.__exit__(None, None, None)


app = FastAPI(title="QuoteFlow API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().public_base_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


def _workflow_graph():
    graph = getattr(app.state, "quote_workflow", None)
    if graph is None:
        checkpointer, _ = make_checkpointer()
        graph = build_workflow(checkpointer)
        app.state.quote_workflow = graph
    return graph


def _brief_from_payload(db: Session, workspace_id: str, payload: BriefCreate) -> Brief:
    client = Client(
        workspace_id=workspace_id,
        name=payload.company_name,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
    )
    db.add(client)
    db.flush()
    brief = Brief(
        workspace_id=workspace_id,
        client_id=client.id,
        source_type=payload.source_type,
        source_text=payload.text,
    )
    db.add(brief)
    db.flush()
    db.add(BriefRevision(brief_id=brief.id, number=1, source_text=brief.source_text))
    db.commit()
    return brief


def _approval_json(item: Approval, db: Session) -> dict:
    version = db.get(QuoteVersion, item.quote_version_id)
    quote = db.get(Quote, version.quote_id) if version else None
    return {
        "id": item.id,
        "quote_version_id": item.quote_version_id,
        "quote_id": version.quote_id if version else None,
        "brief_id": quote.brief_id if quote else None,
        "content_hash": item.content_hash,
        "status": item.status,
        "note": item.note,
        "created_at": timestamp(item.created_at),
        "decided_at": timestamp(item.decided_at),
        "total": str(version.total) if version else None,
        "currency": document_settings(version.proposal)["currency"] if version else "USD",
    }


def _locked_scoped_quote(db: Session, quote_id: str, workspace_id: str) -> Quote:
    """Serialize quote mutations so a portal response sees the latest committed version."""
    quote = db.scalar(
        select(Quote)
        .where(Quote.id == quote_id, Quote.workspace_id == workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if quote is None:
        raise HTTPException(404, "Quote not found")
    return quote


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "mode": get_settings().mode.upper(),
        "synthetic": get_settings().mode.upper() == "DEMO",
    }


@app.get("/api/studio-settings")
def get_studio_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    settings, revision = studio_settings(db, user.workspace_id)
    return {"settings": settings.model_dump(), "revision": revision}


@app.put("/api/studio-settings")
def update_studio_settings(
    payload: StudioUpdate, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    # Lock the workspace row as well, including when no preferences row exists yet.
    from .models import Workspace

    db.scalar(select(Workspace).where(Workspace.id == user.workspace_id).with_for_update())
    record = db.get(WorkspacePreference, user.workspace_id, populate_existing=True)
    revision = record.revision if record else 0
    if revision != payload.expected_revision:
        raise HTTPException(409, "Studio settings changed in another session. Reload before saving.")
    if record is None:
        record = WorkspacePreference(workspace_id=user.workspace_id)
        db.add(record)
    record.settings = payload.settings.model_dump()
    record.revision = revision + 1
    db.commit()
    return {"settings": record.settings, "revision": record.revision}


@app.post("/api/auth/demo")
def auth_demo(payload: DemoLogin, response: Response, db: Session = Depends(get_db)):
    user = demo_user(db, payload.workspace, payload.role)
    issue_session(db, user, response)
    return {
        "user": {"id": user.id, "display_name": user.display_name, "email": user.email},
        "workspace": {"id": user.workspace_id, "name": "Arc & Field Studio", "synthetic": True},
        "role": user.role,
    }


@app.post("/api/auth/login")
def auth_login(payload: Login, response: Response, db: Session = Depends(get_db)):
    user = login(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(401, "Invalid credentials")
    issue_session(db, user, response)
    return {
        "user": {"id": user.id, "display_name": user.display_name, "email": user.email},
        "workspace": {"id": user.workspace_id},
        "role": user.role,
    }


@app.get("/api/auth/me")
def auth_me(user: User = Depends(current_user)):
    return {
        "user": {"id": user.id, "display_name": user.display_name, "email": user.email},
        "workspace": {"id": user.workspace_id},
        "role": user.role,
    }


@app.post("/api/auth/logout")
def auth_logout(response: Response, request: Request, db: Session = Depends(get_db)):
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        record = db.scalar(
            select(SessionRecord).where(SessionRecord.token_hash == token_digest(raw))
        )
        if record is not None:
            db.delete(record)
            db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "logged_out"}


@app.get("/api/briefs")
def list_briefs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Brief)
        .where(Brief.workspace_id == user.workspace_id)
        .order_by(Brief.created_at.desc())
    ).all()
    return {"items": [serialize_brief(db, row) for row in rows]}


@app.post("/api/briefs", status_code=201)
def create_brief(
    payload: BriefCreate,
    user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db),
):
    return serialize_brief(db, _brief_from_payload(db, user.workspace_id, payload), detail=True)


@app.post("/api/public/briefs", status_code=201)
def create_public_demo_brief(payload: BriefCreate, db: Session = Depends(get_db)):
    if get_settings().mode.upper() != "DEMO":
        raise HTTPException(404, "Public demo form is disabled")
    return serialize_brief(db, _brief_from_payload(db, "arc-field-demo", payload), detail=True)


@app.post("/api/briefs/upload", status_code=201)
async def upload_brief(
    file: UploadFile = File(...),
    user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db),
):
    raw = await file.read(get_settings().max_upload_bytes + 1)
    if len(raw) > get_settings().max_upload_bytes:
        raise HTTPException(413, "Upload exceeds the configured size limit")
    if file.content_type != "application/pdf" or not raw.startswith(b"%PDF-"):
        raise HTTPException(415, "Only PDF uploads are supported")
    try:
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted or len(reader.pages) > 40:
            raise ValueError("Encrypted or oversized PDF")
        extracted = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        raise HTTPException(422, "Unable to extract safe PDF text") from exc
    if len(extracted) < 20:
        raise HTTPException(422, "PDF contains too little selectable text")
    payload = BriefCreate(
        source_type="paste",
        text=extracted[:100000],
        company_name=Path(file.filename or "Uploaded brief").stem[:200],
    )
    return serialize_brief(db, _brief_from_payload(db, user.workspace_id, payload), detail=True)


@app.get("/api/briefs/{brief_id}")
def get_brief(brief_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return serialize_brief(db, get_scoped_brief(db, brief_id, user.workspace_id), detail=True)


@app.post("/api/briefs/{brief_id}/analyze")
def analyze(
    brief_id: str, user: User = Depends(require_role("operator")), db: Session = Depends(get_db)
):
    return analyze_brief(db, get_scoped_brief(db, brief_id, user.workspace_id))


@app.get("/api/briefs/{brief_id}/clarifications")
def list_clarifications(
    brief_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    brief = get_scoped_brief(db, brief_id, user.workspace_id)
    return {"items": [serialize_clarification(item) for item in brief.clarifications]}


@app.post("/api/briefs/{brief_id}/clarifications", status_code=201)
def create_clarification(
    brief_id: str,
    payload: ClarificationCreate,
    user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db),
):
    brief = get_scoped_brief(db, brief_id, user.workspace_id)
    item = Clarification(brief_id=brief.id, question=payload.question, affects=["scope", "price"])
    db.add(item)
    brief.status = "needs_clarification"
    db.commit()
    return serialize_clarification(item)


@app.patch("/api/briefs/{brief_id}/clarifications/{clarification_id}")
def edit_clarification(
    brief_id: str,
    clarification_id: str,
    payload: ClarificationEdit,
    user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db),
):
    get_scoped_brief(db, brief_id, user.workspace_id)
    item = db.scalar(
        select(Clarification).where(
            Clarification.id == clarification_id, Clarification.brief_id == brief_id
        )
    )
    if item is None:
        raise HTTPException(404, "Clarification not found")
    if payload.question is not None:
        if len(payload.question.strip()) < 5:
            raise HTTPException(422, "Question is too short")
        item.question = payload.question.strip()
    if payload.answer is not None:
        return serialize_clarification(record_clarification_answer(db, item, payload.answer))
    db.commit()
    return serialize_clarification(item)


@app.post("/api/briefs/{brief_id}/clarifications/{clarification_id}/answer")
def answer_clarification(
    brief_id: str,
    clarification_id: str,
    payload: Answer,
    user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db),
):
    return edit_clarification(
        brief_id, clarification_id, ClarificationEdit(answer=payload.answer), user, db
    )


@app.post("/api/briefs/{brief_id}/portal-link")
def clarification_portal_link(
    brief_id: str, user: User = Depends(require_role("operator")), db: Session = Depends(get_db)
):
    brief = get_scoped_brief(db, brief_id, user.workspace_id)
    raw = issue_portal_token(
        db,
        workspace_id=brief.workspace_id,
        client_id=brief.client_id,
        kind="clarification",
        brief=brief,
    )
    return {"token": raw, "portal_url": f"{get_settings().public_base_url}/portal/{raw}"}


@app.post("/api/briefs/{brief_id}/options")
def options(
    brief_id: str, user: User = Depends(require_role("operator")), db: Session = Depends(get_db)
):
    return generate_options(db, get_scoped_brief(db, brief_id, user.workspace_id))


@app.get("/api/quotes/{quote_id}")
def get_quote(quote_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return serialize_quote(db, get_scoped_quote(db, quote_id, user.workspace_id))


@app.patch("/api/quotes/{quote_id}/versions/{version_id}")
def patch_version(
    quote_id: str,
    version_id: str,
    payload: VersionEdit,
    user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db),
):
    quote = _locked_scoped_quote(db, quote_id, user.workspace_id)
    return replace_version(db, quote, get_scoped_version(db, quote, version_id), payload)


@app.post("/api/quotes/{quote_id}/versions/{version_id}/price-preview")
def price_preview(
    quote_id: str,
    version_id: str,
    payload: VersionEdit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    quote = get_scoped_quote(db, quote_id, user.workspace_id)
    return preview_version(db, get_scoped_version(db, quote, version_id), payload)


@app.get("/api/quotes/{quote_id}/diff")
def quote_diff(
    quote_id: str,
    from_version: str = Query(alias="from"),
    to_version: str = Query(alias="to"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    quote = get_scoped_quote(db, quote_id, user.workspace_id)
    old = get_scoped_version(db, quote, from_version)
    new = get_scoped_version(db, quote, to_version)
    old_lines = {line.service_code: line for line in old.lines}
    new_lines = {line.service_code: line for line in new.lines}
    return {
        "from_version": old.id,
        "to_version": new.id,
        "added_lines": [
            line.service_name for code, line in new_lines.items() if code not in old_lines
        ],
        "removed_lines": [
            line.service_name for code, line in old_lines.items() if code not in new_lines
        ],
        "changed_lines": [
            {
                "service": code,
                "old_quantity": str(old_lines[code].quantity),
                "new_quantity": str(new_lines[code].quantity),
                "old_total": str(old_lines[code].line_total),
                "new_total": str(new_lines[code].line_total),
            }
            for code in old_lines.keys() & new_lines.keys()
            if old_lines[code].quantity != new_lines[code].quantity
            or old_lines[code].line_total != new_lines[code].line_total
        ],
        "total_delta": str(new.total - old.total),
        "proposal_changes": [
            key
            for key in set(old.proposal) | set(new.proposal)
            if old.proposal.get(key) != new.proposal.get(key)
        ],
    }


@app.post("/api/quotes/{quote_id}/versions/{version_id}/submit-review")
def submit_review(
    quote_id: str,
    version_id: str,
    user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db),
):
    quote = _locked_scoped_quote(db, quote_id, user.workspace_id)
    version = get_scoped_version(db, quote, version_id)
    if version.status not in ("draft", "pending_review"):
        raise HTTPException(409, "Only a current draft option can be reviewed")
    existing = db.scalar(
        select(Approval).where(
            Approval.quote_version_id == version.id, Approval.content_hash == version.content_hash
        )
    )
    if existing is None:
        existing = Approval(
            workspace_id=user.workspace_id,
            quote_version_id=version.id,
            content_hash=version.content_hash,
        )
        db.add(existing)
    version.status = "pending_review"
    db.commit()
    return _approval_json(existing, db)


@app.get("/api/approvals")
def approvals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Approval)
        .where(Approval.workspace_id == user.workspace_id)
        .order_by(Approval.created_at.desc())
    ).all()
    return {"items": [_approval_json(item, db) for item in rows]}


@app.post("/api/approvals/{approval_id}/decision")
def decide_approval(
    approval_id: str,
    payload: Decision,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    approval = db.scalar(
        select(Approval).where(Approval.id == approval_id, Approval.workspace_id == user.workspace_id)
    )
    if approval is None:
        raise HTTPException(404, "Approval not found")
    version = db.get(QuoteVersion, approval.quote_version_id)
    if version is None:
        raise HTTPException(409, "Approval is stale")
    quote = _locked_scoped_quote(db, version.quote_id, user.workspace_id)
    db.expire_all()
    approval = db.scalar(
        select(Approval)
        .where(Approval.id == approval_id, Approval.workspace_id == user.workspace_id)
        .with_for_update()
    )
    version = db.get(QuoteVersion, approval.quote_version_id) if approval else None
    if (
        approval is None
        or version is None
        or quote.workspace_id != user.workspace_id
        or version.content_hash != approval.content_hash
        or version.status not in ("pending_review", "approved")
    ):
        raise HTTPException(409, "Approval is stale")
    if approval.status != "pending":
        raise HTTPException(409, "Approval already decided")
    approval.status = payload.decision
    approval.note = payload.note
    approval.decided_by = user.id
    approval.decided_at = now()
    version.status = "approved" if payload.decision == "approved" else "draft"
    db.commit()
    return _approval_json(approval, db)


@app.post("/api/quotes/{quote_id}/versions/{version_id}/publish")
def publish(
    quote_id: str,
    version_id: str,
    user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db),
):
    quote = _locked_scoped_quote(db, quote_id, user.workspace_id)
    version = get_scoped_version(db, quote, version_id)
    if quote.status in ("accepted", "revision_requested") or version.status in (
        "superseded",
        "rejected",
    ):
        raise HTTPException(409, "Only the current unaccepted version can be published")
    approval = db.scalar(
        select(Approval).where(
            Approval.quote_version_id == version.id, Approval.content_hash == version.content_hash
        )
    )
    if (version.approval_required or approval is not None) and (
        approval is None or approval.status != "approved"
    ):
        raise HTTPException(409, "Current quote version requires internal approval")
    client = db.get(Client, quote.client_id)
    if client is None:
        raise HTTPException(404, "Client not found")
    pdf_bytes = render_proposal_pdf(version, client_name=client.name, brief_reference=quote.brief_id)
    asset_dir = Path(get_settings().asset_dir).resolve() / user.workspace_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset_path = asset_dir / f"{version.id}.pdf"
    asset_path.write_bytes(pdf_bytes)
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    asset = db.scalar(
        select(ProposalAsset).where(
            ProposalAsset.quote_version_id == version.id, ProposalAsset.kind == "pdf"
        )
    )
    if asset is None:
        asset = ProposalAsset(
            workspace_id=user.workspace_id,
            quote_version_id=version.id,
            path=str(asset_path),
            content_hash=digest,
        )
        db.add(asset)
    else:
        asset.path = str(asset_path)
        asset.content_hash = digest
    for previous in db.scalars(
        select(CustomerReviewToken).where(
            CustomerReviewToken.quote_version_id == version.id,
            CustomerReviewToken.status == "active",
        )
    ):
        previous.status = "replaced"
    version.status = "published"
    for alternative in quote.versions:
        if alternative.id != version.id and alternative.status in (
            "draft",
            "pending_review",
            "approved",
            "published",
        ):
            alternative.status = "superseded"
            for old_token in db.scalars(
                select(CustomerReviewToken).where(
                    CustomerReviewToken.quote_version_id == alternative.id,
                    CustomerReviewToken.status == "active",
                )
            ):
                old_token.status = "replaced"
    quote.status = "published"
    key = f"proposal-published:{version.id}"
    if db.scalar(select(OutboxEvent).where(OutboxEvent.idempotency_key == key)) is None:
        db.add(
            OutboxEvent(
                workspace_id=user.workspace_id,
                event_type="proposal.published",
                idempotency_key=key,
                payload={
                    "quote_id": quote.id,
                    "version_id": version.id,
                    "client_id": quote.client_id,
                    "simulated": get_settings().mode.upper() == "DEMO",
                },
            )
        )
    db.commit()
    token = issue_portal_token(
        db,
        workspace_id=user.workspace_id,
        client_id=quote.client_id,
        kind="review",
        quote_version=version,
    )
    api_base = get_settings().api_base_url.rstrip("/")
    if not api_base.endswith("/api"):
        api_base += "/api"
    return {
        "token": token,
        "portal_url": f"{get_settings().public_base_url}/portal/{token}",
        "pdf_url": f"{api_base}/quotes/{quote.id}/versions/{version.id}/pdf",
        "asset_id": asset.id,
    }


@app.get("/api/quotes/{quote_id}/versions/{version_id}/pdf")
def download_pdf(
    quote_id: str,
    version_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    quote = get_scoped_quote(db, quote_id, user.workspace_id)
    version = get_scoped_version(db, quote, version_id)
    asset = db.scalar(
        select(ProposalAsset).where(
            ProposalAsset.quote_version_id == version.id,
            ProposalAsset.workspace_id == user.workspace_id,
        )
    )
    if asset is None or not Path(asset.path).is_file():
        raise HTTPException(404, "Published PDF not found")
    return FileResponse(
        asset.path, media_type="application/pdf", filename=f"Arc-Field-Proposal-{version.id}.pdf"
    )


@app.get("/api/portal/{token}")
def view_portal(token: str, db: Session = Depends(get_db)):
    record = portal_record(db, token)
    client = db.get(Client, record.client_id)
    if client is None:
        raise HTTPException(410, "Review client is unavailable")
    if record.kind == "clarification":
        brief = db.get(Brief, record.brief_id)
        if brief is None:
            raise HTTPException(410, "Review brief is unavailable")
        return {
            "kind": "clarification",
            "studio_name": studio_settings(db, record.workspace_id)[0].studio_name,
            "client_name": client.name,
            "brief": serialize_brief(db, brief, detail=True),
            "clarifications": [serialize_clarification(item) for item in brief.clarifications],
            "expires_at": timestamp(record.expires_at),
            "status": record.status,
            "synthetic": get_settings().mode.upper() == "DEMO",
        }
    version = db.get(QuoteVersion, record.quote_version_id)
    if version is None:
        raise HTTPException(410, "Review version is unavailable")
    return {
        "kind": "review",
        "client_name": client.name,
        "quote_version": serialize_version(db, version),
        "expires_at": timestamp(record.expires_at),
        "status": record.status,
        "synthetic": get_settings().mode.upper() == "DEMO",
    }


@app.post("/api/portal/{token}/clarifications/{clarification_id}/answer")
@app.post("/api/portal/{token}/clarifications/{clarification_id}")
def portal_answer(
    token: str, clarification_id: str, payload: Answer, db: Session = Depends(get_db)
):
    record = portal_record(db, token)
    if record.kind != "clarification":
        raise HTTPException(403, "Link cannot answer clarifications")
    item = db.scalar(
        select(Clarification).where(
            Clarification.id == clarification_id, Clarification.brief_id == record.brief_id
        )
    )
    if item is None:
        raise HTTPException(404, "Clarification not found")
    return serialize_clarification(record_clarification_answer(db, item, payload.answer))


@app.post("/api/portal/{token}/response")
def portal_response(token: str, payload: PortalDecision, db: Session = Depends(get_db)):
    record = portal_record(db, token)
    if record.kind != "review":
        raise HTTPException(403, "Link is for clarification only")
    version = db.get(QuoteVersion, record.quote_version_id)
    if version is None:
        raise HTTPException(410, "Review version is unavailable")
    _locked_scoped_quote(db, version.quote_id, record.workspace_id)
    # Another request may have replaced the token or accepted the quote while
    # this request waited on the quote lock. Recheck after acquiring it.
    db.expire_all()
    record = portal_record(db, token)
    version = db.get(QuoteVersion, record.quote_version_id)
    if version is None:
        raise HTTPException(410, "Review version is unavailable")
    quote = db.get(Quote, version.quote_id)
    if quote is None:
        raise HTTPException(410, "Review quote is unavailable")
    if record.status == "accepted" and payload.decision == "accepted":
        existing = db.scalar(
            select(ProjectHandoff).where(ProjectHandoff.quote_version_id == version.id)
        )
        return {"status": "accepted", "handoff_id": existing.id if existing else None}
    if record.status != "active" or version.status != "published" or quote.status != "published":
        raise HTTPException(409, "Review response is already finalized or stale")
    if payload.decision == "accepted":
        quote.status = "accepted"
        quote.accepted_version_id = version.id
        version.status = "accepted"
        record.status = "accepted"
        handoff = db.scalar(
            select(ProjectHandoff).where(ProjectHandoff.quote_version_id == version.id)
        )
        if handoff is None:
            handoff = ProjectHandoff(
                workspace_id=quote.workspace_id,
                client_id=quote.client_id,
                quote_version_id=version.id,
                summary={
                    "quote_id": quote.id,
                    "catalog_version_id": version.catalog_version_id,
                    "content_hash": version.content_hash,
                    "total": str(version.total),
                },
            )
            db.add(handoff)
            db.flush()
        record_local_handoff(
            db,
            workspace_id=quote.workspace_id,
            client_id=quote.client_id,
            version_id=version.id,
            quote_id=quote.id,
            total=str(version.total),
        )
        db.commit()
        return {
            "status": "accepted",
            "handoff_id": handoff.id,
            "workflow": _resume_customer_jobs(db, quote),
        }
    record.status = payload.decision
    quote.status = payload.decision
    key = f"customer-response:{version.id}:{payload.decision}"
    if db.scalar(select(OutboxEvent).where(OutboxEvent.idempotency_key == key)) is None:
        db.add(
            OutboxEvent(
                workspace_id=quote.workspace_id,
                event_type=f"proposal.{payload.decision}",
                idempotency_key=key,
                payload={
                    "quote_id": quote.id,
                    "comment": payload.comment,
                    "simulated": get_settings().mode.upper() == "DEMO",
                },
            )
        )
    db.commit()
    return {
        "status": payload.decision,
        "handoff_id": None,
        "workflow": _resume_customer_jobs(db, quote),
    }


def _resume_customer_jobs(db: Session, quote: Quote) -> list[dict]:
    results = []
    jobs = db.scalars(
        select(Job).where(
            Job.workspace_id == quote.workspace_id,
            Job.kind == "quote_flow",
            Job.status == "waiting_customer_review",
        )
    ).all()
    for job in jobs:
        if job.payload.get("quote_id") == quote.id:
            results.append(
                invoke_job(_workflow_graph(), db, job, resume={"response": quote.status})
            )
    return results


@app.get("/api/handoffs")
def list_handoffs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ProjectHandoff)
        .where(ProjectHandoff.workspace_id == user.workspace_id)
        .order_by(ProjectHandoff.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": row.id,
                "client_id": row.client_id,
                "quote_version_id": row.quote_version_id,
                "summary": row.summary,
                "created_at": timestamp(row.created_at),
            }
            for row in rows
        ]
    }


@app.get("/api/outbox")
def list_outbox(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.workspace_id == user.workspace_id)
        .order_by(OutboxEvent.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": row.id,
                "event_type": row.event_type,
                "payload": row.payload,
                "status": row.status,
                "attempts": row.attempts,
                "last_error": row.last_error,
                "provider_id": row.provider_id,
                "next_attempt_at": timestamp(row.next_attempt_at),
            }
            for row in rows
        ]
    }


def _catalog_json(db: Session, workspace_id: str, version_id: str | None = None) -> dict:
    version = latest_catalog(db, workspace_id) if not version_id else db.scalar(
        select(ServiceCatalogVersion).where(
            ServiceCatalogVersion.id == version_id,
            ServiceCatalogVersion.workspace_id == workspace_id,
        )
    )
    if version is None:
        raise HTTPException(404, "Catalog version not found")
    services = catalog_entries(db, version.id)
    return {
        "version": {"id": version.id, "number": version.number},
        "services": [
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "category": item.category,
                "description": item.description,
                "unit": item.unit,
                "base_price": str(item.base_price),
                "active": item.active,
            }
            for item in services
        ],
    }


@app.get("/api/catalog")
@app.get("/api/catalog/services")
def get_catalog(version_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _catalog_json(db, user.workspace_id, version_id)


def _new_catalog_version(
    db: Session, workspace_id: str, *, replace_id: str | None, replacement: ServiceEdit
) -> dict:
    old = latest_catalog(db, workspace_id)
    entries = catalog_entries(db, old.id)
    if replace_id and not any(item.id == replace_id for item in entries):
        raise HTTPException(404, "Catalog service not found")
    if any(item.code == replacement.code and item.id != replace_id for item in entries):
        raise HTTPException(409, "Catalog service code already exists")
    try:
        price = decimal(replacement.base_price, name="base_price")
    except PricingError as exc:
        raise HTTPException(422, str(exc)) from exc
    if price < 0:
        raise HTTPException(422, "base_price must be nonnegative")
    next_version = ServiceCatalogVersion(workspace_id=workspace_id, number=old.number + 1)
    db.add(next_version)
    db.flush()
    for entry in entries:
        values = (
            replacement.model_dump()
            if entry.id == replace_id
            else {
                "code": entry.code,
                "name": entry.name,
                "category": entry.category,
                "description": entry.description,
                "unit": entry.unit,
                "base_price": str(entry.base_price),
                "active": entry.active,
            }
        )
        db.add(
            ServiceCatalogEntry(
                version_id=next_version.id,
                code=values["code"],
                name=values["name"],
                category=values["category"],
                description=values["description"],
                unit=values["unit"],
                base_price=decimal(values["base_price"]),
                active=values["active"],
            )
        )
    if replace_id is None:
        db.add(
            ServiceCatalogEntry(
                version_id=next_version.id,
                code=replacement.code,
                name=replacement.name,
                category=replacement.category,
                description=replacement.description,
                unit=replacement.unit,
                base_price=price,
                active=replacement.active,
            )
        )
    db.commit()
    return _catalog_json(db, workspace_id)


@app.post("/api/catalog/services", status_code=201)
def create_catalog_service(
    payload: ServiceEdit, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return _new_catalog_version(db, user.workspace_id, replace_id=None, replacement=payload)


@app.patch("/api/catalog/services/{service_id}")
def edit_catalog_service(
    service_id: str,
    payload: ServiceEdit,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return _new_catalog_version(db, user.workspace_id, replace_id=service_id, replacement=payload)


def _csv_safe(value: object) -> str:
    text_value = str(value)
    probe = text_value.lstrip(" \t\r\n")
    return "'" + text_value if probe.startswith(("=", "+", "-", "@")) else text_value


@app.get("/api/quotes/{quote_id}/versions/{version_id}/csv")
def export_quote_csv(
    quote_id: str,
    version_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    quote = get_scoped_quote(db, quote_id, user.workspace_id)
    version = get_scoped_version(db, quote, version_id)
    if version.status not in ("published", "accepted", "approved"):
        raise HTTPException(409, "Only a reviewed version can be exported")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "quote_id",
            "quote_version_id",
            "catalog_version_id",
            "service_code",
            "service_name",
            "quantity",
            "unit_price",
            "line_total",
            "assumption",
        ]
    )
    for line in version.lines:
        writer.writerow(
            [
                _csv_safe(item)
                for item in (
                    quote.id,
                    version.id,
                    version.catalog_version_id,
                    line.service_code,
                    line.service_name,
                    line.quantity,
                    line.unit_price,
                    line.line_total,
                    line.assumption,
                )
            ]
        )
    writer.writerow(["", "", "", "", "TOTAL", "", "", str(version.total), ""])
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="QuoteFlow-{version.id}.csv"'},
    )


@app.get("/api/connectors/health")
def connector_health(user: User = Depends(require_role("admin"))):
    settings = get_settings()
    connected = settings.mode.upper() == "CONNECTED"
    return {
        "mode": settings.mode.upper(),
        "hubspot": {
            "configured": bool(
                connected and settings.hubspot_enabled and settings.hubspot_access_token
            ),
            "status": "configured_unverified"
            if connected and settings.hubspot_enabled and settings.hubspot_access_token
            else "disconnected",
        },
        "model": {
            "configured": bool(connected and settings.openai_api_key and settings.openai_model),
            "status": "configured_unverified"
            if connected and settings.openai_api_key and settings.openai_model
            else "disconnected",
        },
        "outbox": "simulated" if not connected else "durable_worker",
    }


@app.post("/api/outbox/{event_id}/reconcile")
def reconcile_outbox(
    event_id: str,
    delivered: bool,
    provider_id: str | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    event = db.scalar(
        select(OutboxEvent)
        .where(OutboxEvent.id == event_id, OutboxEvent.workspace_id == user.workspace_id)
        .with_for_update()
    )
    if event is None:
        raise HTTPException(404, "Outbox event not found")
    if event.status != "uncertain":
        raise HTTPException(409, "Only uncertain outcomes need reconciliation")
    if delivered and not provider_id:
        raise HTTPException(422, "A delivered event needs a provider ID")
    event.status = "delivered" if delivered else "pending"
    event.provider_id = provider_id if delivered else None
    event.next_attempt_at = None
    event.last_error = (
        "Reconciled by admin as delivered"
        if delivered
        else "Reconciled by admin as not sent; retry allowed"
    )
    db.commit()
    return {"id": event.id, "status": event.status, "provider_id": event.provider_id}


def _job_json(job: Job) -> dict:
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "progress": job.progress,
        "failure_reason": job.failure_reason,
        "payload": job.payload,
        "created_at": timestamp(job.created_at),
    }


@app.post("/api/workflows/briefs/{brief_id}/start", status_code=201)
def start_workflow(
    brief_id: str, user: User = Depends(require_role("operator")), db: Session = Depends(get_db)
):
    # Lock the brief before checking active runs so two simultaneous starts for
    # the same brief cannot both create jobs.
    brief = db.scalar(
        select(Brief)
        .where(Brief.id == brief_id, Brief.workspace_id == user.workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if brief is None:
        raise HTTPException(404, "Brief not found")
    active = db.scalars(
        select(Job)
        .where(
            Job.workspace_id == user.workspace_id,
            Job.kind == "quote_flow",
            Job.status.not_in(("completed", "failed", "cancelled")),
        )
        .order_by(Job.created_at.desc())
    ).all()
    existing = next((job for job in active if job.payload.get("brief_id") == brief_id), None)
    if existing is not None:
        return _job_json(existing)
    job = Job(
        workspace_id=user.workspace_id,
        kind="quote_flow",
        status="running",
        progress=5,
        payload={"brief_id": brief_id},
    )
    db.add(job)
    db.commit()
    return invoke_job(_workflow_graph(), db, job)


@app.get("/api/workflows/{job_id}")
def get_workflow_job(
    job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    job = db.scalar(select(Job).where(Job.id == job_id, Job.workspace_id == user.workspace_id))
    if job is None:
        raise HTTPException(404, "Workflow run not found")
    return _job_json(job)


@app.post("/api/workflows/{job_id}/resume")
def resume_workflow(
    job_id: str,
    payload: dict,
    user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db),
):
    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.workspace_id == user.workspace_id).with_for_update()
    )
    if job is None:
        raise HTTPException(404, "Workflow run not found")
    if not job.status.startswith("waiting_"):
        raise HTTPException(409, "Workflow is not waiting for input")
    kind = job.payload.get("waiting_kind")
    if kind == "internal_review" and user.role != "admin":
        raise HTTPException(403, "Admin role required for internal review")
    if kind == "customer_review":
        raise HTTPException(403, "Customer response must come through the scoped portal")
    if kind == "internal_review":
        value: object = payload.get("version_id")
    elif kind == "clarification":
        value = payload.get("answers", {})
    else:
        value = payload
    job.status = "running"
    db.commit()
    return invoke_job(_workflow_graph(), db, job, resume=value)


@app.post("/api/workflows/{job_id}/cancel")
def cancel_workflow(
    job_id: str, user: User = Depends(require_role("operator")), db: Session = Depends(get_db)
):
    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.workspace_id == user.workspace_id).with_for_update()
    )
    if job is None:
        raise HTTPException(404, "Workflow run not found")
    if job.status in ("completed", "failed"):
        raise HTTPException(409, "Workflow already finished")
    job.status = "cancelled" if job.status.startswith("waiting_") else "cancel_requested"
    db.commit()
    return _job_json(job)


@app.get("/api/workflows/{job_id}/events")
async def workflow_events(
    job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    job = db.scalar(select(Job).where(Job.id == job_id, Job.workspace_id == user.workspace_id))
    if job is None:
        raise HTTPException(404, "Workflow run not found")

    async def stream():
        last = ""
        from .db import SessionLocal

        for _ in range(30):
            with SessionLocal() as session:
                current = session.scalar(
                    select(Job).where(Job.id == job_id, Job.workspace_id == user.workspace_id)
                )
                if current is None:
                    break
                state = _job_json(current)
            encoded = json.dumps(state, separators=(",", ":"))
            if encoded != last:
                yield f"event: status\ndata: {encoded}\n\n"
                last = encoded
            if state["status"] in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(1)

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )
