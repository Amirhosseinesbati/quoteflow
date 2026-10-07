"""QuoteFlow application use cases and JSON projections."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import token_digest
from .config import get_settings
from .extraction import make_extractor
from .models import (
    Approval,
    Brief,
    BriefRevision,
    Clarification,
    CustomerReviewToken,
    Quote,
    QuoteLine,
    QuoteVersion,
    Requirement,
    ServiceCatalogEntry,
    ServiceCatalogVersion,
    now,
)
from .pricing import PricingError, calculate, content_hash, decimal
from .proposals import draft_proposal, estimate_quantity, match_services
from .schemas import VersionEdit
from .studio import document_settings, document_snapshot, studio_settings


def timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def serialize_clarification(item: Clarification) -> dict:
    return {
        "id": item.id,
        "question": item.question,
        "answer": item.answer,
        "status": item.status,
        "affects": item.affects,
        "created_at": timestamp(item.created_at),
    }


def serialize_brief(db: Session, brief: Brief, *, detail: bool = False) -> dict:
    quote = db.scalar(
        select(Quote).where(Quote.brief_id == brief.id, Quote.workspace_id == brief.workspace_id)
    )
    result = {
        "id": brief.id,
        "workspace_id": brief.workspace_id,
        "client_id": brief.client_id,
        "client_name": brief.client.name,
        "company_name": brief.client.name,
        "contact_name": brief.client.contact_name,
        "contact_email": brief.client.contact_email,
        "source_type": brief.source_type,
        "source_text": brief.source_text,
        "text": brief.source_text,
        "status": brief.status,
        "revision_number": brief.revision_number,
        "quote_id": quote.id if quote else None,
        "created_at": timestamp(brief.created_at),
        "extracted": brief.extracted,
    }
    if detail:
        result["requirements"] = [
            {
                "id": r.id,
                "text": r.text,
                "kind": r.kind,
                "evidence": r.evidence,
                "start": r.start,
                "end": r.end,
                "confidence": r.confidence,
            }
            for r in brief.requirements
        ]
        result["clarifications"] = [serialize_clarification(c) for c in brief.clarifications]
    else:
        result["requirements"] = []
        result["clarifications"] = []
    return result


def serialize_line(item: QuoteLine) -> dict:
    return {
        "id": item.id,
        "position": item.position,
        "service_id": item.service_id,
        "service_code": item.service_code,
        "service_name": item.service_name,
        "quantity": str(item.quantity),
        "unit_price": str(item.unit_price),
        "assumption": item.assumption,
        "line_total": str(item.line_total),
    }


def serialize_version(db: Session, version: QuoteVersion) -> dict:
    approval = db.scalar(
        select(Approval).where(
            Approval.quote_version_id == version.id, Approval.content_hash == version.content_hash
        )
    )
    return {
        "id": version.id,
        "quote_id": version.quote_id,
        "number": version.number,
        "label": version.label,
        "status": version.status,
        "proposal": version.proposal,
        "catalog_version_id": version.catalog_version_id,
        "source_version_id": version.source_version_id,
        "content_hash": version.content_hash,
        "lines": [serialize_line(line) for line in version.lines],
        "discount_percent": str(version.discount_percent),
        "tax_percent": str(version.tax_percent),
        "contingency_percent": str(version.contingency_percent),
        "subtotal": str(version.subtotal),
        "discount_amount": str(version.discount_amount),
        "tax_amount": str(version.tax_amount),
        "contingency_amount": str(version.contingency_amount),
        "total": str(version.total),
        "approval_required": version.approval_required,
        "approved": bool(approval and approval.status == "approved"),
        "created_at": timestamp(version.created_at),
    }


def serialize_quote(db: Session, quote: Quote) -> dict:
    versions = sorted(quote.versions, key=lambda version: version.number)
    return {
        "id": quote.id,
        "brief_id": quote.brief_id,
        "client_id": quote.client_id,
        "status": quote.status,
        "accepted_version_id": quote.accepted_version_id,
        "latest_version_id": versions[-1].id if versions else None,
        "versions": [serialize_version(db, version) for version in versions],
    }


def latest_catalog(db: Session, workspace_id: str) -> ServiceCatalogVersion:
    version = db.scalar(
        select(ServiceCatalogVersion)
        .where(ServiceCatalogVersion.workspace_id == workspace_id)
        .order_by(ServiceCatalogVersion.number.desc())
    )
    if version is None:
        raise HTTPException(503, "Service catalog is not initialized")
    return version


def catalog_entries(db: Session, version_id: str) -> list[ServiceCatalogEntry]:
    return list(
        db.scalars(
            select(ServiceCatalogEntry)
            .where(ServiceCatalogEntry.version_id == version_id)
            .order_by(ServiceCatalogEntry.category, ServiceCatalogEntry.name)
        )
    )


def analyze_brief(db: Session, brief: Brief) -> dict:
    catalog = catalog_entries(db, latest_catalog(db, brief.workspace_id).id)
    try:
        extracted = make_extractor(get_settings()).extract(
            brief.source_text, [item.name for item in catalog]
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    # The extractor may fail in CONNECTED mode. Never substitute synthetic results.
    brief.extracted = extracted.model_dump()
    brief.status = "needs_clarification" if extracted.missing_information else "analyzed"
    for existing in list(brief.requirements):
        db.delete(existing)
    db.flush()
    for requirement in extracted.requirements:
        db.add(Requirement(brief_id=brief.id, **requirement.model_dump()))
    open_questions = {item.question for item in brief.clarifications if item.status == "open"}
    for question in extracted.missing_information:
        if question not in open_questions:
            db.add(
                Clarification(
                    brief_id=brief.id, question=question, affects=["scope", "schedule", "price"]
                )
            )
    revision = db.scalar(
        select(BriefRevision).where(
            BriefRevision.brief_id == brief.id, BriefRevision.number == brief.revision_number
        )
    )
    if revision:
        revision.extracted = extracted.model_dump()
    db.commit()
    db.refresh(brief)
    return serialize_brief(db, brief, detail=True)


def _pricing_fields(priced: dict) -> dict:
    return {
        key: decimal(priced[key])
        for key in (
            "discount_percent",
            "tax_percent",
            "contingency_percent",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "contingency_amount",
            "total",
        )
    }


def _make_version(
    db: Session,
    quote: Quote,
    *,
    number: int,
    label: str,
    proposal: dict,
    line_data: list[dict],
    catalog_version_id: str,
    source_version_id: str | None = None,
    discount_percent: str = "0",
    tax_percent: str = "0",
    contingency_percent: str = "0",
) -> QuoteVersion:
    studio, _ = studio_settings(db, quote.workspace_id)
    proposal = {"_document": document_snapshot(studio), **proposal}
    try:
        priced = calculate(
            line_data,
            discount_percent=discount_percent,
            tax_percent=tax_percent,
            contingency_percent=contingency_percent,
        )
    except PricingError as exc:
        raise HTTPException(422, str(exc)) from exc
    noncatalog = any(not line.get("service_id") for line in priced["lines"])
    approval_required = noncatalog or decimal(priced["discount_percent"]) > decimal(
        studio.approval_discount_threshold
    )
    version = QuoteVersion(
        quote_id=quote.id,
        number=number,
        label=label,
        status="draft",
        proposal=proposal,
        catalog_version_id=catalog_version_id,
        source_version_id=source_version_id,
        approval_required=approval_required,
        content_hash=content_hash(proposal, priced["lines"], priced, catalog_version_id),
        **_pricing_fields(priced),
    )
    db.add(version)
    db.flush()
    for position, line in enumerate(priced["lines"]):
        db.add(
            QuoteLine(
                version_id=version.id,
                position=position,
                service_id=line.get("service_id"),
                service_code=line.get("service_code") or "custom",
                service_name=line["service_name"],
                quantity=decimal(line["quantity"]),
                unit_price=decimal(line["unit_price"]),
                assumption=line.get("assumption", ""),
                line_total=decimal(line["line_total"]),
            )
        )
    db.flush()
    return version


def generate_options(db: Session, brief: Brief) -> dict:
    if not brief.extracted:
        analyze_brief(db, brief)
    # The brief lock serializes first-time quote creation; existing quote edits
    # use the same quote-row lock as publication and customer responses.
    locked_brief = db.scalar(
        select(Brief)
        .where(Brief.id == brief.id, Brief.workspace_id == brief.workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked_brief is None:
        raise HTTPException(404, "Brief not found")
    brief = locked_brief
    if any(c.status == "open" for c in brief.clarifications):
        raise HTTPException(
            409, "Answer or close the open clarification questions before generating options"
        )
    existing = db.scalar(
        select(Quote)
        .where(Quote.brief_id == brief.id, Quote.workspace_id == brief.workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if existing and existing.status == "accepted":
        raise HTTPException(409, "Accepted quote is immutable")
    catalog_version = latest_catalog(db, brief.workspace_id)
    catalog = catalog_entries(db, catalog_version.id)
    matched = match_services(brief, catalog)
    if len(matched) < 3:
        raise HTTPException(422, "Catalog needs at least three active services")
    quote = existing or Quote(
        workspace_id=brief.workspace_id, client_id=brief.client_id, brief_id=brief.id
    )
    if existing is None:
        db.add(quote)
        db.flush()
    else:
        for version in quote.versions:
            if version.status in ("draft", "pending_review", "approved", "published"):
                version.status = "superseded"
        token_ids = [version.id for version in quote.versions]
        for token in db.scalars(
            select(CustomerReviewToken).where(CustomerReviewToken.quote_version_id.in_(token_ids))
        ):
            token.status = "replaced"
    current = max((version.number for version in quote.versions), default=0)
    selections = [matched[:3], matched[:5], matched[:6]]
    labels = ["Essential", "Recommended", "Comprehensive"]
    versions = []
    for offset, (label, services) in enumerate(zip(labels, selections, strict=True), start=1):
        lines = [
            {
                "service_id": item.id,
                "service_code": item.code,
                "service_name": item.name,
                "quantity": estimate_quantity(brief, item),
                "unit_price": str(item.base_price),
                "assumption": f"{estimate_quantity(brief, item)} {item.unit}(s), one agreed review cycle; client supplies final inputs.",
            }
            for item in services
        ]
        proposal = draft_proposal(brief, brief.client.name, label, services)
        version = _make_version(
            db,
            quote,
            number=current + offset,
            label=label,
            proposal=proposal,
            line_data=lines,
            catalog_version_id=catalog_version.id,
            tax_percent=studio_settings(db, brief.workspace_id)[0].default_tax_percent,
            contingency_percent=studio_settings(db, brief.workspace_id)[0].default_contingency_percent,
        )
        versions.append(version)
    quote.status = "options_ready"
    brief.status = "options_ready"
    db.commit()
    return {
        "quote_id": quote.id,
        "options": [serialize_version(db, version) for version in versions],
    }


def record_clarification_answer(db: Session, item: Clarification, answer: str) -> Clarification:
    normalized = answer.strip()
    if not normalized:
        raise HTTPException(422, "Answer cannot be blank")
    brief = db.scalar(
        select(Brief)
        .where(Brief.id == item.brief_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if brief is None:
        raise HTTPException(404, "Brief not found")
    db.refresh(item)
    if item.answer == normalized:
        return item
    quote = db.scalar(
        select(Quote)
        .where(Quote.brief_id == brief.id, Quote.workspace_id == brief.workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if quote and quote.status == "accepted":
        raise HTTPException(409, "Accepted proposal is immutable; start a new brief")
    item.answer = normalized
    item.status = "answered"
    item.answered_at = now()
    brief.revision_number += 1
    extracted = {**brief.extracted}
    responses = dict(extracted.get("clarification_answers", {}))
    responses[item.id] = normalized
    extracted["clarification_answers"] = responses
    brief.extracted = extracted
    db.add(
        BriefRevision(
            brief_id=brief.id,
            number=brief.revision_number,
            source_text=brief.source_text,
            extracted=extracted,
        )
    )
    if quote and quote.versions:
        base = max(
            (version for version in quote.versions if version.status != "superseded"),
            key=lambda version: version.number,
            default=max(quote.versions, key=lambda version: version.number),
        )
        proposal = {"_document": document_settings(base.proposal), **base.proposal}
        assumptions = list(proposal.get("assumptions", []))
        assumptions = [
            value
            for value in assumptions
            if not str(value).startswith(f"Clarified: {item.question} —")
        ]
        assumptions.append(f"Clarified: {item.question} — {normalized}")
        proposal["assumptions"] = assumptions
        if any(term in item.question.lower() for term in ("timeline", "launch date", "schedule")):
            proposal["schedule"] = normalized
        lines = [serialize_line(line) for line in base.lines]
        _make_version(
            db,
            quote,
            number=max(version.number for version in quote.versions) + 1,
            label=base.label,
            proposal=proposal,
            line_data=lines,
            catalog_version_id=base.catalog_version_id,
            source_version_id=base.id,
            discount_percent=str(base.discount_percent),
            tax_percent=str(base.tax_percent),
            contingency_percent=str(base.contingency_percent),
        )
        for old in quote.versions:
            if old.status in ("draft", "pending_review", "approved", "published"):
                old.status = "superseded"
            for token in db.scalars(
                select(CustomerReviewToken).where(
                    CustomerReviewToken.quote_version_id == old.id,
                    CustomerReviewToken.status == "active",
                )
            ):
                token.status = "replaced"
        quote.status = "revision_requested"
        brief.status = "revised"
    else:
        brief.status = (
            "needs_clarification"
            if any(c.status == "open" for c in brief.clarifications)
            else "analyzed"
        )
    db.commit()
    return item


def _line_input(db: Session, version: QuoteVersion, raw: dict) -> dict:
    service_id = raw.get("service_id")
    service_code = raw.get("service_code")
    service = None
    if service_id:
        service = db.scalar(
            select(ServiceCatalogEntry).where(
                ServiceCatalogEntry.id == service_id,
                ServiceCatalogEntry.version_id == version.catalog_version_id,
                ServiceCatalogEntry.active.is_(True),
            )
        )
    elif service_code:
        service = db.scalar(
            select(ServiceCatalogEntry).where(
                ServiceCatalogEntry.code == service_code,
                ServiceCatalogEntry.version_id == version.catalog_version_id,
                ServiceCatalogEntry.active.is_(True),
            )
        )
    if service_id and service is None:
        raise HTTPException(422, "Service is not in the quote catalog version")
    price = str(service.base_price) if service else raw.get("unit_price")
    if price is None:
        raise HTTPException(422, "A noncatalog line needs an explicit unit_price")
    return {
        "service_id": service.id if service else None,
        "service_code": service.code if service else (service_code or "custom"),
        "service_name": service.name if service else raw["service_name"],
        "quantity": raw.get("quantity", "1"),
        "unit_price": price,
        "assumption": raw.get("assumption", ""),
    }


def preview_version(db: Session, version: QuoteVersion, edit: VersionEdit) -> dict:
    raw_lines = (
        [line.model_dump() for line in edit.lines]
        if edit.lines is not None
        else [serialize_line(line) for line in version.lines]
    )
    line_data = [_line_input(db, version, raw) for raw in raw_lines]
    try:
        priced = calculate(
            line_data,
            discount_percent=edit.discount_percent or str(version.discount_percent),
            tax_percent=edit.tax_percent or str(version.tax_percent),
            contingency_percent=edit.contingency_percent or str(version.contingency_percent),
        )
    except PricingError as exc:
        raise HTTPException(422, str(exc)) from exc
    priced["approval_required"] = any(not line.get("service_id") for line in line_data) or decimal(
        priced["discount_percent"]
    ) > decimal(studio_settings(db, version.quote.workspace_id)[0].approval_discount_threshold)
    return priced


def replace_version(db: Session, quote: Quote, version: QuoteVersion, edit: VersionEdit) -> dict:
    if quote.status == "accepted" or version.status == "accepted":
        raise HTTPException(409, "Accepted quote is immutable")
    if version.status in ("superseded", "rejected"):
        raise HTTPException(409, "This option has been replaced")
    if edit.proposal is not None:
        for key, value in edit.proposal.items():
            if key == "_document":
                if value != version.proposal.get("_document"):
                    raise HTTPException(422, "Document identity is frozen; generate new options to apply studio settings")
            elif not isinstance(value, str | list) or (
                isinstance(value, list) and any(not isinstance(item, str) for item in value)
            ):
                raise HTTPException(422, "Proposal sections must contain text or a list of text")
    preview = preview_version(db, version, edit)
    proposal = {"_document": document_settings(version.proposal), **version.proposal, **(edit.proposal or {})}
    new_version = _make_version(
        db,
        quote,
        number=max(v.number for v in quote.versions) + 1,
        label=edit.label or version.label,
        proposal=proposal,
        line_data=preview["lines"],
        catalog_version_id=version.catalog_version_id,
        source_version_id=version.id,
        discount_percent=preview["discount_percent"],
        tax_percent=preview["tax_percent"],
        contingency_percent=preview["contingency_percent"],
    )
    for old in quote.versions:
        if old.id == new_version.id:
            continue
        if old.status in ("draft", "pending_review", "approved", "published"):
            old.status = "superseded"
        for token in db.scalars(
            select(CustomerReviewToken).where(
                CustomerReviewToken.quote_version_id == old.id,
                CustomerReviewToken.status == "active",
            )
        ):
            token.status = "replaced"
    db.commit()
    return serialize_version(db, new_version)


def get_scoped_brief(db: Session, brief_id: str, workspace_id: str) -> Brief:
    brief = db.scalar(select(Brief).where(Brief.id == brief_id, Brief.workspace_id == workspace_id))
    if brief is None:
        raise HTTPException(404, "Brief not found")
    return brief


def get_scoped_quote(db: Session, quote_id: str, workspace_id: str) -> Quote:
    quote = db.scalar(select(Quote).where(Quote.id == quote_id, Quote.workspace_id == workspace_id))
    if quote is None:
        raise HTTPException(404, "Quote not found")
    return quote


def get_scoped_version(db: Session, quote: Quote, version_id: str) -> QuoteVersion:
    version = db.scalar(
        select(QuoteVersion).where(QuoteVersion.id == version_id, QuoteVersion.quote_id == quote.id)
    )
    if version is None:
        raise HTTPException(404, "Quote version not found")
    return version


def issue_portal_token(
    db: Session,
    *,
    workspace_id: str,
    client_id: str,
    kind: str,
    quote_version: QuoteVersion | None = None,
    brief: Brief | None = None,
) -> str:
    raw = secrets.token_urlsafe(40)
    db.add(
        CustomerReviewToken(
            workspace_id=workspace_id,
            client_id=client_id,
            quote_version_id=quote_version.id if quote_version else None,
            brief_id=brief.id if brief else None,
            token_hash=token_digest(raw),
            content_hash=quote_version.content_hash if quote_version else "",
            kind=kind,
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().portal_ttl_days),
        )
    )
    db.commit()
    return raw


def portal_record(db: Session, raw: str) -> CustomerReviewToken:
    token = db.scalar(
        select(CustomerReviewToken).where(CustomerReviewToken.token_hash == token_digest(raw))
    )
    if token is None:
        raise HTTPException(404, "Review link not found")
    expiry = (
        token.expires_at.replace(tzinfo=UTC)
        if token.expires_at.tzinfo is None
        else token.expires_at.astimezone(UTC)
    )
    if expiry <= datetime.now(UTC):
        raise HTTPException(410, "Review link expired")
    if token.status == "replaced":
        raise HTTPException(410, "Review link was replaced")
    if token.status not in ("active", "accepted", "declined", "revision_requested"):
        raise HTTPException(410, "Review link inactive")
    if token.kind == "review":
        version = db.get(QuoteVersion, token.quote_version_id)
        quote = db.get(Quote, version.quote_id) if version else None
        if (
            version is None
            or quote is None
            or quote.workspace_id != token.workspace_id
            or quote.client_id != token.client_id
            or version.content_hash != token.content_hash
        ):
            raise HTTPException(410, "Review link no longer matches its quote")
        active = db.scalar(
            select(func.max(QuoteVersion.number)).where(
                QuoteVersion.quote_id == quote.id,
                QuoteVersion.status.not_in(("superseded", "rejected")),
            )
        )
        if active != version.number and quote.accepted_version_id != version.id:
            raise HTTPException(410, "Review link refers to a replaced version")
    else:
        brief = db.get(Brief, token.brief_id)
        if (
            brief is None
            or brief.workspace_id != token.workspace_id
            or brief.client_id != token.client_id
        ):
            raise HTTPException(410, "Clarification link no longer matches its brief")
    return token
