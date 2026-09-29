"""Deterministic catalog pricing. Money never passes through binary floats."""

from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class PricingError(ValueError):
    pass


def decimal(value: Any, *, name: str = "value") -> Decimal:
    if isinstance(value, float):
        raise PricingError(f"{name} must be a decimal string, not a float")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise PricingError(f"{name} is not a valid decimal") from exc
    if not result.is_finite():
        raise PricingError(f"{name} must be finite")
    return result


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def percent(value: Any, name: str) -> Decimal:
    parsed = decimal(value, name=name)
    if parsed < 0 or parsed > 100:
        raise PricingError(f"{name} must be between 0 and 100")
    if parsed != parsed.quantize(CENT):
        raise PricingError(f"{name} supports at most two decimal places")
    return parsed


def calculate(
    lines: list[dict[str, Any]],
    *,
    discount_percent: Any = "0",
    tax_percent: Any = "0",
    contingency_percent: Any = "0",
) -> dict[str, Any]:
    if not lines:
        raise PricingError("A quote needs at least one line")
    discount = percent(discount_percent, "discount_percent")
    tax = percent(tax_percent, "tax_percent")
    contingency = percent(contingency_percent, "contingency_percent")
    priced = []
    subtotal = ZERO
    for line in lines:
        quantity = decimal(line.get("quantity", "1"), name="quantity")
        unit_price = decimal(line.get("unit_price"), name="unit_price")
        if quantity <= 0 or unit_price < 0:
            raise PricingError("quantity must be positive and unit price nonnegative")
        if quantity != quantity.quantize(CENT) or unit_price != unit_price.quantize(CENT):
            raise PricingError("quantity and unit_price support at most two decimal places")
        line_total = money(quantity * unit_price)
        subtotal += line_total
        priced.append(
            {
                **line,
                "quantity": str(quantity),
                "unit_price": str(money(unit_price)),
                "line_total": str(line_total),
            }
        )
    subtotal = money(subtotal)
    discount_amount = money(subtotal * discount / 100)
    base = subtotal - discount_amount
    contingency_amount = money(base * contingency / 100)
    tax_amount = money((base + contingency_amount) * tax / 100)
    total = money(base + contingency_amount + tax_amount)
    return {
        "lines": priced,
        "discount_percent": str(discount),
        "tax_percent": str(tax),
        "contingency_percent": str(contingency),
        "subtotal": str(subtotal),
        "discount_amount": str(discount_amount),
        "contingency_amount": str(contingency_amount),
        "tax_amount": str(tax_amount),
        "total": str(total),
    }


def content_hash(proposal: dict, lines: list[dict], pricing: dict, catalog_version_id: str) -> str:
    content = {
        "proposal": proposal,
        "lines": [
            {
                key: line.get(key)
                for key in (
                    "service_code",
                    "service_name",
                    "quantity",
                    "unit_price",
                    "assumption",
                    "line_total",
                )
            }
            for line in lines
        ],
        "pricing": {
            key: pricing[key]
            for key in (
                "discount_percent",
                "tax_percent",
                "contingency_percent",
                "subtotal",
                "discount_amount",
                "contingency_amount",
                "tax_amount",
                "total",
            )
        },
        "catalog_version_id": catalog_version_id,
    }
    raw = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()
