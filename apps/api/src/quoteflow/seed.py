"""Idempotent synthetic demo seed. Evaluation labels are never loaded."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Brief,
    BriefRevision,
    Client,
    ProjectHandoff,
    Quote,
    QuoteLine,
    QuoteVersion,
    ServiceCatalogEntry,
    ServiceCatalogVersion,
    User,
    Workspace,
)
from .pricing import calculate, content_hash, decimal

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA = ROOT / "data" / "generated"
PASSWORD = "DemoQuote2026!"


def catalog_entry_id(workspace_id: str, code: str) -> str:
    return hashlib.sha256(f"{workspace_id}:{code}".encode()).hexdigest()[:32]


FALLBACK_CATALOG = [
    ("brand-identity", "Visual identity system", "Branding", "project", "8400"),
    ("web-discovery", "Website discovery", "Website design", "workshop", "1300"),
    ("web-design", "Responsive page design", "Website design", "page", "1200"),
    ("web-build", "CMS page implementation", "Website design", "page", "1500"),
    ("web-analytics", "Analytics implementation", "Website design", "project", "1450"),
    ("intake-crm", "CRM contact sync", "Integrations", "integration", "2800"),
    ("care-essential", "Essential care", "Maintenance", "month", "450"),
]


def _load(path: Path, name: str) -> list[dict]:
    file = path / f"{name}.json"
    if not file.exists():
        raise FileNotFoundError(
            f"Full demo dataset missing: {file}. Run scripts/generate_demo.py first."
        )
    value = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"Expected list in {file}")
    return value


def seed_demo(
    session: Session,
    *,
    full: bool = False,
    data_path: Path | None = None,
    reference_date: date | None = None,
) -> dict[str, int]:
    del reference_date  # Dataset generator owns the configurable reference date.
    path = data_path or DEFAULT_DATA
    workspace_specs = [
        ("arc-field-demo", "Arc & Field Studio"),
        ("arc-field-isolation", "Arc & Field Isolation"),
    ]
    for slug, name in workspace_specs:
        if session.get(Workspace, slug) is None:
            session.add(Workspace(id=slug, slug=slug, name=name, is_demo=True))
    session.flush()
    hasher = PasswordHash.recommended()
    hashed = hasher.hash(PASSWORD)
    for slug, _ in workspace_specs:
        for role in ("admin", "operator", "viewer"):
            email = f"{role}@{slug}.example.com"
            if (
                session.scalar(select(User).where(User.workspace_id == slug, User.email == email))
                is None
            ):
                session.add(
                    User(
                        workspace_id=slug,
                        email=email,
                        display_name=f"Demo {role.title()}",
                        password_hash=hashed,
                        role=role,
                    )
                )
    catalog_data: list[dict[str, Any]] = (
        _load(path, "catalog")
        if full
        else (
            json.loads((path / "catalog.json").read_text(encoding="utf-8"))
            if (path / "catalog.json").exists()
            else [
                {
                    "id": code,
                    "name": name,
                    "category": category,
                    "unit": unit,
                    "unit_price": price,
                    "description": "Fictional studio service",
                    "active": True,
                }
                for code, name, category, unit, price in FALLBACK_CATALOG
            ]
        )
    )
    for slug, _ in workspace_specs:
        version_id = f"catalog:{slug}:1"
        if session.get(ServiceCatalogVersion, version_id) is None:
            session.add(ServiceCatalogVersion(id=version_id, workspace_id=slug, number=1))
        session.flush()
        for data in catalog_data:
            entry_id = catalog_entry_id(slug, data["id"])
            if session.get(ServiceCatalogEntry, entry_id) is None:
                session.add(
                    ServiceCatalogEntry(
                        id=entry_id,
                        version_id=version_id,
                        code=data["id"],
                        name=data["name"],
                        category=data["category"],
                        unit=data.get("unit", "project"),
                        description=data.get("description", ""),
                        base_price=decimal(data["unit_price"]),
                        active=data.get("active", True),
                    )
                )
    session.flush()
    if not full:
        if session.scalar(select(Client).where(Client.workspace_id == "arc-field-demo")) is None:
            client = Client(
                workspace_id="arc-field-demo",
                name="Juniper Grove",
                contact_name="Avery Lee",
                contact_email="avery@juniper-grove.example.com",
            )
            session.add(client)
            session.flush()
            brief = Brief(
                workspace_id=client.workspace_id,
                client_id=client.id,
                source_type="paste",
                source_text="We need a six-page responsive website with CRM contact sync in twelve weeks. Our budget is $18,000-$28,000. We can supply photography and a draft sitemap.",
            )
            session.add(brief)
            session.flush()
            session.add(BriefRevision(brief_id=brief.id, number=1, source_text=brief.source_text))
        session.commit()
        return {"catalog": len(catalog_data), "clients": 1}

    for data in _load(path, "clients"):
        if session.get(Client, data["id"]) is None:
            session.add(
                Client(
                    id=data["id"],
                    workspace_id=data["workspace_id"],
                    name=data["name"],
                    contact_name=data.get("contact_name", ""),
                    contact_email=data.get("contact_email", ""),
                )
            )
    session.flush()
    for data in _load(path, "briefs"):
        if session.get(Brief, data["id"]) is None:
            created = datetime.fromisoformat(data["submitted_at"])
            brief = Brief(
                id=data["id"],
                workspace_id=data["workspace_id"],
                client_id=data["client_id"],
                source_type=data["source"],
                source_text=data["text"],
                created_at=created,
            )
            session.add(brief)
            session.add(
                BriefRevision(
                    brief_id=data["id"], number=1, source_text=data["text"], created_at=created
                )
            )
    session.flush()
    quote_rows = _load(path, "quotes")
    for data in quote_rows:
        if session.get(Quote, data["id"]) is None:
            session.add(
                Quote(
                    id=data["id"],
                    workspace_id=data["workspace_id"],
                    client_id=data["client_id"],
                    brief_id=data["brief_id"],
                    status=data.get("status", "draft"),
                    accepted_version_id=data["selected_version"]
                    if data.get("status") == "accepted"
                    else None,
                )
            )
    session.flush()
    for data in _load(path, "quote_versions"):
        if session.get(QuoteVersion, data["id"]) is not None:
            continue
        quote = session.get(Quote, data["quote_id"])
        if quote is None:
            raise ValueError("Missing quote in generated dataset")
        lines = [
            {
                "service_id": catalog_entry_id(quote.workspace_id, line["service_id"]),
                "service_code": line["service_id"],
                "service_name": line["name"],
                "quantity": str(line["quantity"]),
                "unit_price": line["unit_price"],
                "assumption": line.get("assumption", ""),
            }
            for line in data["line_items"]
        ]
        priced = calculate(
            lines,
            discount_percent=data.get("discount_percent", "0"),
            tax_percent=data.get("tax_percent", "0"),
            contingency_percent=data.get("contingency_percent", "0"),
        )
        proposal = {
            "executive_summary": data["summary"],
            "objectives": ["Deliver the agreed brief"],
            "scope": data["summary"],
            "deliverables": [line["name"] for line in data["line_items"]],
            "exclusions": ["Unlisted services"],
            "assumptions": ["Client supplies final content"],
            "schedule": "To be agreed",
            "milestones": ["Discovery", "Review", "Handoff"],
            "client_responsibilities": ["Provide timely feedback"],
            "acceptance_steps": ["Review and acknowledge this scope"],
        }
        version = QuoteVersion(
            id=data["id"],
            quote_id=quote.id,
            number=data["version"],
            label=data["option"],
            status=data["status"],
            proposal=proposal,
            catalog_version_id=f"catalog:{quote.workspace_id}:1",
            discount_percent=decimal(priced["discount_percent"]),
            tax_percent=decimal(priced["tax_percent"]),
            contingency_percent=decimal(priced["contingency_percent"]),
            subtotal=decimal(priced["subtotal"]),
            discount_amount=decimal(priced["discount_amount"]),
            contingency_amount=decimal(priced["contingency_amount"]),
            tax_amount=decimal(priced["tax_amount"]),
            total=decimal(priced["total"]),
            approval_required=False,
            content_hash=content_hash(
                proposal, priced["lines"], priced, f"catalog:{quote.workspace_id}:1"
            ),
        )
        session.add(version)
        for position, line in enumerate(priced["lines"]):
            session.add(
                QuoteLine(
                    version_id=data["id"],
                    position=position,
                    service_id=line["service_id"],
                    service_code=line["service_code"],
                    service_name=line["service_name"],
                    quantity=decimal(line["quantity"]),
                    unit_price=decimal(line["unit_price"]),
                    assumption=line["assumption"],
                    line_total=decimal(line["line_total"]),
                )
            )
    session.flush()
    for data in _load(path, "handoffs"):
        if session.get(ProjectHandoff, data["id"]) is None:
            session.add(
                ProjectHandoff(
                    id=data["id"],
                    workspace_id=data["workspace_id"],
                    client_id=data["client_id"],
                    quote_version_id=data["quote_version_id"],
                    summary={"source": "synthetic full dataset", "quote_id": data["quote_id"]},
                )
            )
    session.commit()
    return {
        "catalog": len(catalog_data),
        "clients": 50,
        "briefs": 120,
        "quotes": 80,
        "versions": 180,
        "handoffs": 30,
    }
