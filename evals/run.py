"""Validate synthetic fixtures and, optionally, measure the DEMO extractor.

Fixture integrity is a deterministic check. DEMO extraction scores are scoped to the
authored synthetic cases and must not be represented as live-customer accuracy.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENT = Decimal("0.01")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def fixture_checks(source: Path) -> dict:
    parts = {name: read(source / f"{name}.json") for name in
             ("catalog", "clients", "briefs", "quotes", "quote_versions", "handoffs")}
    truth = read(source / "evaluation_only" / "brief_ground_truth.json")
    cases = read(source / "evaluation_only" / "cases.json")
    expected_counts = {"catalog": 35, "clients": 50, "briefs": 120, "quotes": 80,
                       "quote_versions": 180, "handoffs": 30}
    failures: list[str] = []
    for name, expected in expected_counts.items():
        check(len(parts[name]) == expected, f"{name}: expected {expected}, got {len(parts[name])}", failures)
        ids = [row["id"] for row in parts[name]]
        check(len(ids) == len(set(ids)), f"{name}: duplicate IDs", failures)
    check(len(cases) == 90, f"evaluation cases: expected 90, got {len(cases)}", failures)
    check(Counter(case["category"] for case in cases) == {
        "extraction_scope": 40, "pricing_rounding_revision": 30,
        "approval_token_access_retry": 20}, "evaluation category counts", failures)
    check(Counter(case["split"] for case in cases) == {"development": 30, "held_out": 60},
          "development/held-out counts", failures)

    client_by_id = {row["id"]: row for row in parts["clients"]}
    brief_by_id = {row["id"]: row for row in parts["briefs"]}
    quote_by_id = {row["id"]: row for row in parts["quotes"]}
    version_by_id = {row["id"]: row for row in parts["quote_versions"]}
    service_by_id = {row["id"]: row for row in parts["catalog"]}
    truth_by_id = {row["brief_id"]: row for row in truth}

    for brief in parts["briefs"]:
        client = client_by_id.get(brief["client_id"])
        check(client is not None, f"{brief['id']}: missing client", failures)
        if client:
            check(brief["workspace_id"] == client["workspace_id"], f"{brief['id']}: client workspace mismatch", failures)
        check(len(brief["text"].split()) >= 100, f"{brief['id']}: not substantial enough", failures)
    check(sum(len(brief["text"].split()) >= 125 for brief in parts["briefs"][:12]) >= 12,
          "first 12 authored briefs should be detailed", failures)
    for labeled in truth:
        brief = brief_by_id.get(labeled["brief_id"])
        check(brief is not None, f"truth {labeled['brief_id']}: missing brief", failures)
        if not brief:
            continue
        for field, span in labeled["evidence"].items():
            expected = labeled["fields"][field]
            check(brief["text"][span["start"]:span["end"]] == expected,
                  f"{brief['id']}: evidence mismatch for {field}", failures)

    versions_per_quote = Counter()
    for quote in parts["quotes"]:
        brief = brief_by_id.get(quote["brief_id"])
        check(brief is not None, f"{quote['id']}: missing brief", failures)
        if brief:
            check(quote["client_id"] == brief["client_id"] and quote["workspace_id"] == brief["workspace_id"],
                  f"{quote['id']}: brief/client workspace mismatch", failures)
    for version in parts["quote_versions"]:
        quote = quote_by_id.get(version["quote_id"])
        check(quote is not None, f"{version['id']}: missing quote", failures)
        if quote:
            check(version["workspace_id"] == quote["workspace_id"], f"{version['id']}: quote workspace mismatch", failures)
        versions_per_quote[version["quote_id"]] += 1
        subtotal = Decimal(0)
        for line in version["line_items"]:
            service = service_by_id.get(line["service_id"])
            check(service is not None, f"{version['id']}: unknown service", failures)
            if service:
                check(line["unit_price"] == service["unit_price"], f"{version['id']}: catalog price mismatch", failures)
            amount = (Decimal(line["unit_price"]) * Decimal(str(line["quantity"]))).quantize(CENT, rounding=ROUND_HALF_UP)
            check(Decimal(line["amount"]) == amount, f"{version['id']}: line amount mismatch", failures)
            subtotal += amount
        discount = (subtotal * Decimal(version["discount_percent"]) / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        base = subtotal - discount
        contingency = (base * Decimal(version["contingency_percent"]) / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        tax = ((base + contingency) * Decimal(version["tax_percent"]) / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        check(Decimal(version["subtotal"]) == subtotal and Decimal(version["discount_amount"]) == discount
              and Decimal(version["total"]) == base + contingency + tax,
              f"{version['id']}: deterministic total mismatch", failures)
    check(len(versions_per_quote) == 80, "versions must cover 80 quote records", failures)
    for handoff in parts["handoffs"]:
        version = version_by_id.get(handoff["quote_version_id"])
        check(version is not None, f"{handoff['id']}: missing version", failures)
        if version:
            check(version["status"] == "accepted" and version["quote_id"] == handoff["quote_id"]
                  and version["workspace_id"] == handoff["workspace_id"],
                  f"{handoff['id']}: accepted version mismatch", failures)

    extraction_cases = [case for case in cases if case["category"] == "extraction_scope"]
    dev_templates = {brief_by_id[case["brief_id"]]["scenario_template"] for case in extraction_cases
                     if case["split"] == "development"}
    held_templates = {brief_by_id[case["brief_id"]]["scenario_template"] for case in extraction_cases
                      if case["split"] == "held_out"}
    check(dev_templates.isdisjoint(held_templates), "extraction split leaks scenario templates", failures)
    dev_clients = {brief_by_id[case["brief_id"]]["client_id"] for case in extraction_cases
                   if case["split"] == "development"}
    held_clients = {brief_by_id[case["brief_id"]]["client_id"] for case in extraction_cases
                    if case["split"] == "held_out"}
    check(dev_clients.isdisjoint(held_clients), "extraction split leaks client entities", failures)
    check(len({case["brief_id"] for case in extraction_cases}) == 40, "extraction cases duplicate brief IDs", failures)
    check(len(truth_by_id) == 120, "ground truth does not cover 120 briefs", failures)

    return {"mode": "fixture", "reference_date": read(source / "metadata.json")["reference_date"],
            "counts": {name: len(rows) for name, rows in parts.items()}, "evaluation_cases": len(cases),
            "development_cases": 30, "held_out_cases": 60, "checks_passed": len(failures) == 0,
            "failures": failures, "limits": ["Behavioral access/token cases are definitions only in fixture mode.",
                                          "Synthetic integrity does not establish model quality or human review."]}


def demo_extraction(source: Path) -> dict:
    sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
    from quoteflow.extraction import DemoExtractor

    briefs = {item["id"]: item for item in read(source / "briefs.json")}
    cases = [item for item in read(source / "evaluation_only" / "cases.json")
             if item["category"] == "extraction_scope" and item["split"] == "held_out"]
    metadata = read(source / "metadata.json")
    services = [item["name"] for item in read(source / "catalog.json")]
    extractor = DemoExtractor()
    aligned_spans = 0
    predicted = 0
    found = 0
    unadjudicated = 0
    expected = len(cases)
    field_hits = Counter()
    field_total = Counter()
    detail = []
    for case in cases:
        brief = briefs[case["brief_id"]]
        result = extractor.extract(brief["text"], services)
        expected_fields = case["expected"]["fields"]
        deliverables = expected_fields["deliverables"]
        deliverable_span = case["expected"]["evidence"]["deliverables"]
        if brief["text"][deliverable_span["start"]:deliverable_span["end"]] != deliverables:
            raise ValueError(f"{case['id']}: primary deliverable label has an invalid source span")
        found_deliverable = False
        case_aligned = 0
        case_unadjudicated = 0
        for requirement in result.requirements:
            predicted += 1
            evidence = requirement.evidence
            valid_span = (0 <= requirement.start < requirement.end <= len(brief["text"])
                          and brief["text"][requirement.start:requirement.end] == evidence)
            if valid_span:
                aligned_spans += 1
                case_aligned += 1
            covers_label = (valid_span and requirement.kind == "deliverable"
                            and requirement.start <= deliverable_span["start"]
                            and requirement.end >= deliverable_span["end"])
            if covers_label and not found_deliverable:
                found_deliverable = True
            else:
                # Only the primary deliverable is labeled as a requirement. Other predictions
                # could be supported or invented; do not classify them from a substring match.
                unadjudicated += 1
                case_unadjudicated += 1
        found += int(found_deliverable)
        actual = result.model_dump()
        for field, result_key in (("company", "company"), ("contact", "contact"),
                                  ("email", "email"), ("timeline", "timeline"),
                                  ("budget", "budget_range")):
            if result_key not in actual:
                continue
            field_total[field] += 1
            if str(actual[result_key] or "").strip().lower() == str(expected_fields[field]).strip().lower():
                field_hits[field] += 1
        detail.append({"case_id": case["id"], "brief_id": case["brief_id"],
                       "primary_deliverable_found": found_deliverable,
                       "aligned_spans": case_aligned,
                       "unadjudicated_predictions": case_unadjudicated,
                       "expected_deliverable": deliverables if not found_deliverable else None})
    return {"mode": "demo_extraction", "split": "held_out", "cases": expected,
            "extractor": "DemoExtractor", "dataset_seed": metadata["seed"],
            "reference_date": metadata["reference_date"],
            "catalog_version": metadata["catalog_version"],
            "predicted_requirements": predicted,
            "evidence_alignment": {"aligned": aligned_spans, "predicted": predicted,
                                   "rate": aligned_spans / predicted if predicted else None},
            "primary_deliverable_recall": {"found": found, "labeled": expected,
                                            "rate": found / expected if expected else None},
            "unadjudicated_predictions": unadjudicated,
            "full_requirement_precision": None,
            "full_requirement_recall": None,
            "material_fabrications": None,
            "field_exact": {field: {"correct": field_hits[field], "total": field_total[field]}
                            for field in field_total},
            "case_results": detail,
            "limits": ["Evidence alignment checks exact source offsets, not semantic support.",
                       "Primary deliverable recall covers one independently labeled phrase per held-out synthetic brief.",
                       "The labels do not exhaust supported requirements; all other predictions remain unadjudicated, so full requirement precision/recall and material fabrications cannot be calculated.",
                       "Connected-model quality and 10-proposal human review remain separate gates."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fixture", "demo-extraction"), default="fixture")
    parser.add_argument("--source", type=Path, default=ROOT / "data" / "generated")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = fixture_checks(args.source) if args.mode == "fixture" else demo_extraction(args.source)
    output = args.output or ROOT / "evals" / "results" / f"{args.mode}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(result, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(result, indent=2))
    if result.get("failures"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
