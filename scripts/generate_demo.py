"""Reproducible synthetic QuoteFlow dataset. No model calls or external writes."""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


CATALOG = [
    ("brand-discovery", "Branding", "Discovery workshop", "workshop", "1800"),
    ("brand-strategy", "Branding", "Brand strategy", "project", "6200"),
    ("brand-identity", "Branding", "Visual identity system", "project", "8400"),
    ("brand-logo", "Branding", "Logo exploration", "project", "3600"),
    ("brand-guidelines", "Branding", "Brand guidelines", "project", "4300"),
    ("brand-templates", "Branding", "Social template set", "set", "1500"),
    ("brand-packaging", "Branding", "Packaging concept", "concept", "2800"),
    ("brand-copy", "Branding", "Brand voice and copy", "project", "3900"),
    ("web-discovery", "Website design", "Website discovery", "workshop", "1300"),
    ("web-sitemap", "Website design", "Sitemap and content model", "project", "2200"),
    ("web-wireframes", "Website design", "Page wireframes", "page", "650"),
    ("web-design", "Website design", "Responsive page design", "page", "1200"),
    ("web-build", "Website design", "CMS page implementation", "page", "1500"),
    ("web-commerce", "Website design", "Commerce setup", "project", "7600"),
    ("web-accessibility", "Website design", "Accessibility audit", "audit", "2400"),
    ("web-performance", "Website design", "Performance pass", "project", "1900"),
    ("web-seo", "Website design", "Technical SEO setup", "project", "1800"),
    ("web-content", "Website design", "Content migration", "page", "290"),
    ("web-analytics", "Website design", "Analytics implementation", "project", "1450"),
    ("web-training", "Website design", "CMS training", "session", "700"),
    ("intake-forms", "Integrations", "Lead intake form", "form", "1100"),
    ("intake-crm", "Integrations", "CRM contact sync", "integration", "2800"),
    ("intake-calendar", "Integrations", "Calendar booking", "integration", "1600"),
    ("intake-email", "Integrations", "Email automation", "workflow", "1300"),
    ("intake-payment", "Integrations", "Payment gateway setup", "integration", "2700"),
    ("intake-inventory", "Integrations", "Inventory feed", "integration", "4100"),
    ("intake-api", "Integrations", "Custom API connector", "integration", "5200"),
    ("intake-data", "Integrations", "Data import", "source", "1900"),
    ("care-essential", "Maintenance", "Essential care", "month", "450"),
    ("care-growth", "Maintenance", "Growth care", "month", "950"),
    ("care-security", "Maintenance", "Security review", "review", "750"),
    ("care-content", "Maintenance", "Content support", "month", "620"),
    ("care-optimization", "Maintenance", "Conversion optimization", "sprint", "2300"),
    ("care-reporting", "Maintenance", "Performance reporting", "month", "350"),
    ("care-hosting", "Maintenance", "Managed hosting coordination", "month", "320"),
]

CLIENT_NAMES = [
    "Juniper Grove", "Tern & Tide", "Cinder House", "Morrow Pantry", "Blue Finch Lab",
    "Atlas Grove", "Pinewell Health", "Lumen Orchard", "Mosaic Forge", "Fieldnote Books",
    "Harbor Loom", "Briar & Co", "Eastbank Dental", "Foundry Table", "Quiet Current",
    "Nettle Studio", "Northline Coffee", "Pebble Clinic", "Gatherworks", "Lakefold",
    "Copper Fern", "Goodland Goods", "Mica Learning", "Trellis Market", "Canopy Method",
    "Elmstone Partners", "Little Atlas", "Silver Finch", "Hollow & Hearth", "Vista Bloom",
    "Newmoon Press", "Bracken Works", "Mirth Supply", "Oakmile Foods", "Beacon Thread",
    "Dovetail Care", "Salt Meadow", "Fernlight", "Woven Signal", "Riverbend Arts",
    "Grove & Grain", "Paperfox", "Mallow Home", "Sundial Labs", "Cove Athletics",
    "Good Current", "Kindred Path", "The Honey Room", "Northstar Ceramics", "Fable Commons",
]

SCENARIOS = [
    {
        "kind": "Website redesign", "services": ["web-discovery", "web-sitemap", "web-wireframes", "web-design", "web-build", "web-analytics"],
        "deliverables": "a six-page responsive website and a content model", "timeline": "twelve weeks", "budget": "$18,000–$28,000",
        "assets": "a draft sitemap and a folder of approved photography", "constraint": "The existing site must remain live during the transition.",
        "detail": "The navigation has grown around internal teams rather than visitor tasks. Prospects cannot tell which services fit them, and staff currently copy enquiry details between two systems. We want the new structure to make the primary service paths clear, but the copy still needs an internal owner. Please include a practical handover so our team can update routine pages without developer help.",
    },
    {
        "kind": "Visual identity", "services": ["brand-discovery", "brand-strategy", "brand-identity", "brand-guidelines", "brand-templates"],
        "deliverables": "a visual identity, concise guidelines, and social templates", "timeline": "ten weeks", "budget": "$14,000–$24,000",
        "assets": "customer research notes, but no usable vector logo", "constraint": "We need to retain a recognizable reference to the current mark.",
        "detail": "Our services have expanded and the visual system no longer scales across printed material, presentations, and our digital channels. The team has different opinions about how much to preserve. We need a collaborative discovery step, options with clear rationale, and files that an in-house designer can use after handover. Please identify what copywriting and trademark review would remain with us.",
    },
    {
        "kind": "Commerce launch", "services": ["web-discovery", "web-design", "web-build", "web-commerce", "intake-payment", "web-training"],
        "deliverables": "an online shop for twenty initial products", "timeline": "fourteen weeks", "budget": "$25,000–$38,000",
        "assets": "product photos for half the range and a spreadsheet of SKUs", "constraint": "Orders must remain auditable during the switchover.",
        "detail": "The current order process is handled by email, which leads to duplicate requests and inconsistent stock information. We need a storefront that works well on phones, supports a small team, and leaves room for a later inventory connection. Product descriptions and tax rules are being prepared by our staff. Please separate the first launch from optional automation so the price is understandable.",
    },
    {
        "kind": "CRM integration", "services": ["web-discovery", "intake-forms", "intake-crm", "intake-email", "intake-data"],
        "deliverables": "two lead forms and a CRM handoff", "timeline": "eight weeks", "budget": "$9,000–$16,000",
        "assets": "a field map and sample export with test records", "constraint": "Consent wording must be approved by our legal team.",
        "detail": "Sales enquiries arrive from several forms and are manually re-entered. We would like staff to see the source and service interest with each record, and to receive a clear error report when the destination rejects a field. The CRM sandbox is available but production credentials will be provided later. Please state what mapping, deduplication, and acceptance testing you assume.",
    },
    {
        "kind": "Accessibility improvement", "services": ["web-accessibility", "web-wireframes", "web-design", "web-build", "web-training"],
        "deliverables": "an accessibility audit and remediation of four key pages", "timeline": "nine weeks", "budget": "$11,000–$19,000",
        "assets": "access to a staging site and recent customer support themes", "constraint": "The booking journey is highest priority.",
        "detail": "Customers report difficulty using the current navigation and form controls with keyboards and small screens. We need issues prioritized by impact and a practical remediation plan, not a generic score. Our team can update content but cannot change templates. Please allow time for retesting with representative tasks and make clear that ongoing content governance remains our responsibility.",
    },
    {
        "kind": "Content migration", "services": ["web-sitemap", "web-content", "web-seo", "web-build", "web-training"],
        "deliverables": "migration of thirty editorial pages with redirects", "timeline": "eleven weeks", "budget": "$12,000–$20,000",
        "assets": "a content inventory with inconsistent page owners", "constraint": "A seasonal campaign launches before the migration deadline.",
        "detail": "Several pages repeat the same information and old URLs still receive referrals. We want a revised structure and a clean migration, but each page needs an owner to approve final text. Please include a redirect and QA approach, clarify how many revision rounds are included, and show an option that defers lower-priority archive material until after launch.",
    },
    {
        "kind": "Brand and web launch", "services": ["brand-discovery", "brand-identity", "brand-guidelines", "web-sitemap", "web-design", "web-build"],
        "deliverables": "a refreshed identity and five-page website", "timeline": "sixteen weeks", "budget": "$27,000–$42,000",
        "assets": "interview summaries and an old design file", "constraint": "The website cannot launch before the board approves the identity.",
        "detail": "We are bringing three service lines under one name. Each line has different audiences, but we want the site to feel like one organization. The board meets monthly, so presentation milestones matter. Please show an efficient base scope and a fuller option with additional audience research. Our internal team will write technical service descriptions after the information architecture is agreed.",
    },
    {
        "kind": "Booking experience", "services": ["web-discovery", "web-wireframes", "web-design", "intake-calendar", "intake-email", "web-analytics"],
        "deliverables": "a mobile-first booking journey and confirmation messages", "timeline": "seven weeks", "budget": "$10,000–$18,000",
        "assets": "a working calendar account and support ticket examples", "constraint": "Existing appointments must not be lost.",
        "detail": "Visitors often abandon the current request form because it asks the same questions twice. We need to distinguish a request from a confirmed appointment and set clear expectations in the messages. Our operations team will provide availability rules. Please include a testing plan for cancellations and time zones, while keeping payment collection outside this phase.",
    },
    {
        "kind": "Analytics refresh", "services": ["web-analytics", "web-performance", "web-seo", "care-reporting"],
        "deliverables": "an event measurement plan and monthly reporting setup", "timeline": "six weeks", "budget": "$6,000–$11,000",
        "assets": "read-only analytics access and an existing dashboard", "constraint": "Only consented events may be recorded.",
        "detail": "Leadership sees traffic reports but cannot answer which enquiries came from the new content. We need a short measurement plan tied to real decisions, a clean implementation, and a way to explain gaps in the data. The team also wants a baseline on page speed and search health. Please describe dependencies on consent configuration and the limits of attribution.",
    },
    {
        "kind": "Care program", "services": ["care-essential", "care-security", "care-content", "care-reporting"],
        "deliverables": "a six-month website care plan", "timeline": "start next month", "budget": "$4,000–$8,000",
        "assets": "an administrator login and a list of recurring issues", "constraint": "Urgent incidents need a named escalation path.",
        "detail": "Our previous provider handled updates reactively and there is little record of what changed. We need a regular maintenance rhythm, clear monthly reporting, and support for modest content changes. Please distinguish scheduled work from incident response and spell out response-time assumptions. Hosting ownership remains with our IT team for now.",
    },
    {
        "kind": "Packaging concept", "services": ["brand-discovery", "brand-packaging", "brand-copy", "brand-guidelines"],
        "deliverables": "three packaging concepts and print-ready guidance", "timeline": "nine weeks", "budget": "$10,000–$17,000",
        "assets": "dielines for one format and product ingredient text", "constraint": "Regulated claims need separate client approval.",
        "detail": "The product line is growing beyond its original audience. We want the shelf story to become clearer while retaining our familiar color cue. One packaging format is ready; two others are still being finalized with the manufacturer. Please distinguish concept design from print production, note who owns proofing, and show how extra formats would be priced.",
    },
    {
        "kind": "Digital launch campaign", "services": ["brand-copy", "brand-templates", "web-design", "intake-forms", "web-analytics"],
        "deliverables": "a campaign landing page, lead form, and reusable assets", "timeline": "five weeks", "budget": "$8,000–$14,000",
        "assets": "approved key messages and draft campaign imagery", "constraint": "The event date is fixed; no paid media buying is requested.",
        "detail": "A new program opens for registration soon. We need a focused landing page that explains eligibility, handles enquiries, and works with our existing visual style. The internal marketing team will own media placement and ongoing copy edits. Please make any dependencies on final images and legal text visible, and offer a practical fallback if those arrive late.",
    },
]

OPENINGS = [
    "We are reviewing how customers encounter our services and would like a practical proposal.",
    "Our leadership team approved a discovery phase and now needs a costed implementation path.",
    "Please help us turn the attached priorities into a phased scope with clear responsibilities.",
    "We are looking for a partner who can explain the tradeoffs between a focused launch and a broader program.",
]
FOLLOW_UPS = [
    "We would prefer two rounds of feedback on the primary deliverables.",
    "Please show what you assume about content preparation and internal approvals.",
    "The team is distributed across two time zones, so workshop scheduling needs notice.",
    "We want the final files and a short training handover, not a standing retainer by default.",
    "A second stakeholder may join after the first design review.",
    "Our existing vendor will provide access once the project schedule is agreed.",
]


def money(value: Decimal | str | int) -> str:
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_dataset(seed: int, reference_date: date) -> dict[str, object]:
    rng = random.Random(seed)
    catalog = [
        {"id": service_id, "catalog_version": "2026.1", "category": category, "name": name,
         "unit": unit, "unit_price": money(price), "currency": "USD", "active": True,
         "description": f"Fictional studio service: {name.lower()} delivered with agreed review checkpoints."}
        for service_id, category, name, unit, price in CATALOG
    ]
    service_by_id = {item["id"]: item for item in catalog}
    clients = []
    for index, name in enumerate(CLIENT_NAMES):
        slug = name.lower().replace(" & ", "-").replace(" ", "-")
        clients.append({"id": f"client-{index + 1:03}", "workspace_id": "arc-field-demo" if index < 40 else "arc-field-isolation",
                        "name": name, "contact_name": f"{['Avery', 'Morgan', 'Riley', 'Jordan', 'Casey'][index % 5]} {['Lee', 'Patel', 'Chen', 'Rivera', 'Brooks'][index % 5]}",
                        "contact_email": f"hello@{slug}.example.com"})
    briefs = []
    truth = []
    for index in range(120):
        scenario = SCENARIOS[index % len(SCENARIOS)]
        client = clients[(index * 17) % len(clients)]
        detail = scenario["detail"]
        intro = OPENINGS[index % len(OPENINGS)]
        follow_up = FOLLOW_UPS[(index * 7) % len(FOLLOW_UPS)]
        anomaly = ""
        if index % 11 == 0:
            anomaly = "Someone mentioned an immediate launch, although the planning note says the schedule above; please clarify before committing."
        elif index % 13 == 0:
            anomaly = "We are unsure whether the quantity includes alternate language pages; please quote only the stated base scope."
        elif index % 17 == 0:
            anomaly = "We have asked for a discount, but the amount and approval are still open."
        elif index % 19 == 0:
            anomaly = "We may later want a custom booking integration, which is not part of this request."
        text = (f"Subject: {scenario['kind']} for {client['name']}\n\n"
                f"Hello Arc & Field Studio,\n\n{intro} We need {scenario['deliverables']} and hope to complete it in {scenario['timeline']}. "
                f"Our working budget is {scenario['budget']}.\n\n{detail}\n\n"
                f"We can supply {scenario['assets']}. {scenario['constraint']} {follow_up} {anomaly}\n\n"
                f"Please address your response to {client['contact_name']} ({client['contact_email']}).")
        submitted = datetime.combine(reference_date - timedelta(days=200 - index), datetime.min.time(), tzinfo=timezone.utc)
        brief_id = f"brief-{index + 1:03}"
        briefs.append({"id": brief_id, "workspace_id": client["workspace_id"], "client_id": client["id"],
                       "submitted_at": submitted.isoformat(), "source": "pasted_email" if index % 3 else "public_form",
                       "text": text, "synthetic": True, "scenario_template": index % len(SCENARIOS)})
        fields = {
            "company": client["name"], "contact": client["contact_name"], "email": client["contact_email"],
            "deliverables": scenario["deliverables"], "timeline": scenario["timeline"],
            "budget": scenario["budget"], "constraints": [scenario["constraint"]], "assets": scenario["assets"],
        }
        truth.append({"brief_id": brief_id, "fields": fields,
                      "evidence": {key: {"start": text.find(value), "end": text.find(value) + len(value)}
                                   for key, value in fields.items() if isinstance(value, str)},
                      "required_services": scenario["services"],
                      "missing_information": ["final approval owner", "content owner"] + (["timeline conflict"] if index % 11 == 0 else [])})
    quotes = []
    versions = []
    handoffs = []
    for index in range(80):
        brief = briefs[(index * 7) % len(briefs)]
        scenario = SCENARIOS[brief["scenario_template"]]
        count = 3 if index < 20 else 2  # 60 + 120 = 180 versions.
        quote_id = f"quote-{index + 1:03}"
        quotes.append({"id": quote_id, "workspace_id": brief["workspace_id"], "brief_id": brief["id"],
                       "client_id": brief["client_id"], "status": "accepted" if index < 30 else "draft",
                       "selected_version": f"{quote_id}-v{count}"})
        for number in range(1, count + 1):
            selected_services = scenario["services"][: 3 + ((index + number) % 3)]
            lines = []
            for line_index, service_id in enumerate(selected_services):
                service = service_by_id[service_id]
                qty = 1
                if service["unit"] == "page":
                    qty = 4 + ((index + number) % 4)
                elif service["unit"] == "month":
                    qty = 3 + ((index + number) % 4)
                amount = Decimal(service["unit_price"]) * qty
                lines.append({"service_id": service_id, "name": service["name"], "quantity": qty,
                              "unit": service["unit"], "unit_price": service["unit_price"],
                              "amount": money(amount), "assumption": "One agreed review cycle per deliverable; client supplies final content."})
            subtotal = sum((Decimal(line["amount"]) for line in lines), Decimal("0"))
            discount_pct = Decimal("10") if (index + number) % 14 == 0 else Decimal("0")
            discount = (subtotal * discount_pct / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total = subtotal - discount
            version_id = f"{quote_id}-v{number}"
            versions.append({"id": version_id, "quote_id": quote_id, "workspace_id": brief["workspace_id"],
                             "version": number, "catalog_version": "2026.1", "option": ["Essential", "Expanded", "Signature"][(number - 1) % 3],
                             "summary": f"A scoped {scenario['kind'].lower()} engagement for {CLIENT_NAMES[int(brief['client_id'].split('-')[1]) - 1]}.",
                             "line_items": lines, "subtotal": money(subtotal), "discount_percent": money(discount_pct),
                             "discount_amount": money(discount), "tax_percent": "0.00", "tax_amount": "0.00",
                             "contingency_percent": "0.00", "contingency_amount": "0.00", "total": money(total),
                             "currency": "USD", "status": "accepted" if index < 30 and number == count else "draft"})
        if index < 30:
            handoffs.append({"id": f"handoff-{index + 1:03}", "workspace_id": brief["workspace_id"],
                             "quote_id": quote_id, "quote_version_id": f"{quote_id}-v{count}",
                             "client_id": brief["client_id"], "acknowledged_at": (reference_date - timedelta(days=index)).isoformat(),
                             "status": "ready_for_kickoff"})
    return {"metadata": {"title": "Synthetic demo dataset", "company": "Arc & Field Studio", "seed": seed,
                         "reference_date": reference_date.isoformat(), "currency": "USD", "catalog_version": "2026.1"},
            "catalog": catalog, "clients": clients, "briefs": briefs, "truth": truth,
            "quotes": quotes, "quote_versions": versions, "handoffs": handoffs}


def make_evaluation_cases(dataset: dict[str, object]) -> list[dict[str, object]]:
    truth_by_id = {item["brief_id"]: item for item in dataset["truth"]}
    versions = dataset["quote_versions"]
    cases = []
    development_briefs = [i for i, brief in enumerate(dataset["briefs"])
                          if brief["scenario_template"] in {0, 1, 2, 3} and i < 48][:10]
    development_client_ids = {dataset["briefs"][i]["client_id"] for i in development_briefs}
    held_out_briefs = [i for i, brief in enumerate(dataset["briefs"])
                       if brief["scenario_template"] in {4, 5, 6, 7, 8, 9, 10, 11}
                       and brief["client_id"] not in development_client_ids and i >= 48][:30]
    for index, brief_index in enumerate(development_briefs + held_out_briefs):
        # Extraction templates and client entities are disjoint across development/held-out.
        brief = dataset["briefs"][brief_index]
        cases.append({"id": f"extract-{index + 1:02}", "category": "extraction_scope",
                      "split": "development" if index < 10 else "held_out", "brief_id": brief["id"],
                      "expected": truth_by_id[brief["id"]]})
    for index in range(30):
        version = versions[(index * 5) % len(versions)]
        cases.append({"id": f"pricing-{index + 1:02}", "category": "pricing_rounding_revision",
                      "split": "development" if index < 10 else "held_out", "quote_version_id": version["id"],
                      "expected_total": version["total"], "expected_discount": version["discount_amount"],
                      "expected_revision_invalidates_approval": True})
    for index in range(20):
        scenario = ["valid_acceptance", "stale_token", "expired_token", "cross_client_token", "modified_token",
                    "repeated_acceptance", "connector_retry", "unapproved_discount", "noncatalog_line", "viewer_forbidden"][index % 10]
        cases.append({"id": f"access-{index + 1:02}", "category": "approval_token_access_retry",
                      "split": "development" if index < 10 else "held_out", "scenario": scenario,
                      "expected_allowed": scenario in {"valid_acceptance", "repeated_acceptance", "connector_retry"},
                      "expected_handoffs": 1 if scenario in {"valid_acceptance", "repeated_acceptance", "connector_retry"} else 0})
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=90421)
    parser.add_argument("--reference-date", type=date.fromisoformat, default=date(2026, 9, 28))
    parser.add_argument("--output", type=Path, default=Path("data/generated"))
    args = parser.parse_args()
    dataset = make_dataset(args.seed, args.reference_date)
    output = args.output
    write_json(output / "metadata.json", dataset["metadata"])
    for name in ("catalog", "clients", "briefs", "quotes", "quote_versions", "handoffs"):
        write_json(output / f"{name}.json", dataset[name])
    # Held-out labels are kept separate from the runtime data files.
    write_json(output / "evaluation_only" / "brief_ground_truth.json", dataset["truth"])
    cases = make_evaluation_cases(dataset)
    write_json(output / "evaluation_only" / "cases.json", cases)
    print(json.dumps({"output": str(output), "counts": {name: len(dataset[name]) for name in
                     ("catalog", "clients", "briefs", "quotes", "quote_versions", "handoffs")},
                     "eval_cases": len(cases)}, indent=2))


if __name__ == "__main__":
    main()
