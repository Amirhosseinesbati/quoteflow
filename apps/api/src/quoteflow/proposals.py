"""Catalog matching and proposal drafts; the pricing module owns every total."""

from __future__ import annotations

import re
from collections.abc import Sequence

from .extraction import explicit_scope_addition
from .models import Brief, ServiceCatalogEntry

MATCH_TERMS = {
    "brand-discovery": ("brand", "identity"),
    "brand-identity": ("identity", "brand"),
    "brand-logo": ("logo",),
    "brand-guidelines": ("guidelines", "brand"),
    "brand-packaging": ("packaging",),
    "brand-copy": ("copy", "message"),
    "brand-templates": ("template", "social"),
    "web-discovery": ("website", "web", "site"),
    "web-sitemap": ("sitemap", "structure", "navigation"),
    "web-wireframes": ("wireframe", "page", "website"),
    "web-design": ("design", "page", "website", "landing"),
    "web-build": ("build", "website", "page", "cms", "storefront"),
    "web-commerce": ("shop", "storefront", "commerce"),
    "web-accessibility": ("accessibility", "keyboard"),
    "web-performance": ("performance", "speed"),
    "web-seo": ("seo", "search", "redirect"),
    "web-content": ("migration", "content"),
    "web-analytics": ("analytics", "measurement", "tracking"),
    "web-training": ("training", "handover"),
    "intake-forms": ("form", "enquiry"),
    "intake-crm": ("crm",),
    "intake-calendar": ("booking", "calendar"),
    "intake-email": ("email automation", "confirmation"),
    "intake-payment": ("payment",),
    "intake-inventory": ("inventory", "stock"),
    "intake-api": ("api", "connector"),
    "intake-data": ("data import", "export"),
    "care-essential": ("care plan", "maintenance"),
    "care-growth": ("growth care",),
    "care-security": ("security",),
    "care-content": ("content support",),
    "care-optimization": ("conversion",),
    "care-reporting": ("reporting", "report"),
    "care-hosting": ("hosting",),
}

# Quantity answers only affect the named service. A page count for content
# migration, for example, must not silently change website design or build.
QUANTITY_CONTEXT = {
    "web-content": ("migration", "migrate"),
    "web-design": ("design", "layout"),
    "web-build": ("build", "implementation", "implement", "cms"),
    "web-wireframes": ("wireframe",),
    "intake-forms": ("form",),
    "care-essential": ("care plan", "maintenance"),
    "care-growth": ("growth care",),
}

NUMBER = r"(?:\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _scope_additions(brief: Brief) -> list[str]:
    return [
        addition
        for item in brief.clarifications
        if item.status == "answered"
        and "scope" in item.affects
        and (addition := explicit_scope_addition(item.answer)) is not None
    ]


def _names_service(answer: str, service: ServiceCatalogEntry) -> bool:
    lowered = answer.lower()
    if service.name.lower() in lowered:
        return True
    return any(
        re.search(rf"\b{re.escape(term)}\b", lowered)
        for term in QUANTITY_CONTEXT.get(service.code, ())
    )


def _stated_quantity(text: str, unit: str) -> int | None:
    suffixes = {
        "page": r"(?:(?:approved|editorial|content)\s+)*pages?",
        "month": r"months?",
        "form": r"(?:lead\s+)?forms?",
    }
    suffix = suffixes.get(unit)
    if suffix is None:
        return None
    match = re.search(rf"\b({NUMBER})\s*(?:-\s*)?{suffix}\b", text, re.I)
    if match is None:
        return None
    raw = match.group(1).lower()
    return int(raw) if raw.isdecimal() else NUMBER_WORDS[raw]


def match_services(
    brief: Brief, catalog: Sequence[ServiceCatalogEntry]
) -> list[ServiceCatalogEntry]:
    # Original requirements and explicit customer answers retain separate evidence.
    text = " ".join(
        [*(r.text for r in brief.requirements), *_scope_additions(brief)]
    ).lower()
    ranked = []
    for item in catalog:
        if not item.active:
            continue
        terms = MATCH_TERMS.get(item.code, tuple(item.name.lower().split()))
        score = sum(3 if term in text else 0 for term in terms)
        if item.name.lower() in text:
            score += 5
        if score:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: (-pair[0], pair[1].code))
    selected = [item for _, item in ranked[:6]]
    if len(selected) < 6:
        primary_category = selected[0].category if selected else None
        extras = [item for item in catalog if item.active and item not in selected]
        extras.sort(key=lambda item: (item.category != primary_category, item.code))
        selected.extend(extras[: 6 - len(selected)])
    return selected


def estimate_quantity(brief: Brief, service: ServiceCatalogEntry) -> str:
    if service.unit in ("page", "month", "form"):
        for answer in reversed(_scope_additions(brief)):
            if _names_service(answer, service):
                quantity = _stated_quantity(answer, service.unit)
                if quantity is not None:
                    return str(min(quantity, {"page": 100, "month": 24, "form": 20}[service.unit]))
        quantity = _stated_quantity(brief.source_text, service.unit)
        if quantity is not None:
            return str(min(quantity, {"page": 100, "month": 24, "form": 20}[service.unit]))
        return {"page": "4", "month": "3", "form": "1"}[service.unit]
    return "1"


def draft_proposal(
    brief: Brief, client_name: str, label: str, selected: Sequence[ServiceCatalogEntry]
) -> dict:
    names = [item.name for item in selected]
    timeline = brief.extracted.get("timeline") or "Schedule to be confirmed with the client"
    answers = [(item.question, item.answer) for item in brief.clarifications if item.answer]
    for question, answer in answers:
        if any(term in question.lower() for term in ("timeline", "launch date", "schedule")):
            timeline = answer
    constraints = brief.extracted.get("constraints") or []
    assets = brief.extracted.get("supplied_assets") or []
    return {
        "executive_summary": f"Arc & Field Studio proposes the {label.lower()} engagement for {client_name}, based on the supplied brief and the scope shown below.",
        "objectives": [
            "Deliver the agreed scope with clear review checkpoints",
            "Give the client usable handover materials",
        ],
        "scope": f"{label} scope includes: " + ", ".join(names) + ".",
        "deliverables": names,
        "exclusions": [
            "Unlisted services and third-party fees",
            "Legal, trademark, or regulatory sign-off",
            "Additional revision rounds beyond the agreed milestones",
        ],
        "assumptions": [
            "One agreed review cycle per primary deliverable",
            "Final content and access are supplied by the client",
        ]
        + constraints[:2]
        + [f"Clarified: {question} — {answer}" for question, answer in answers],
        "schedule": timeline,
        "milestones": [
            "Discovery and scope confirmation",
            "First deliverable review",
            "Revisions and client acceptance",
            "Final handoff",
        ],
        "client_responsibilities": ["Provide timely feedback and a single approval owner"]
        + (assets[:2] if assets else ["Provide needed source assets and credentials"]),
        "acceptance_steps": [
            "Review the scope, assumptions, exclusions, and total",
            "Use the customer review page to acknowledge acceptance or request changes",
        ],
        "terms": "Sample terms: work starts after a separate services agreement and agreed deposit. This proposal is not legal advice or a certified electronic signature.",
    }
