from decimal import Decimal

import pytest

from quoteflow.main import _csv_safe
from quoteflow.pricing import PricingError, calculate


def test_rounding_discount_contingency_and_tax_are_deterministic():
    priced = calculate(
        [{"service_name": "Design", "quantity": "3", "unit_price": "0.35"}],
        discount_percent="10",
        contingency_percent="5",
        tax_percent="8.25",
    )
    assert priced["subtotal"] == "1.05"
    assert priced["discount_amount"] == "0.11"
    assert priced["contingency_amount"] == "0.05"
    assert priced["tax_amount"] == "0.08"
    assert priced["total"] == "1.07"
    assert Decimal(priced["lines"][0]["line_total"]) == Decimal("1.05")


@pytest.mark.parametrize(
    "lines,discount",
    [
        ([{"quantity": "3", "unit_price": "0.335"}], "0"),
        ([{"quantity": "1.001", "unit_price": "10"}], "0"),
        ([{"quantity": "1", "unit_price": "10"}], "10.001"),
        ([{"quantity": "0", "unit_price": "10"}], "0"),
        ([{"quantity": "1", "unit_price": -1}], "0"),
        ([{"quantity": "1", "unit_price": 1.2}], "0"),
    ],
)
def test_rejects_precision_and_invalid_inputs(lines, discount):
    with pytest.raises(PricingError):
        calculate(lines, discount_percent=discount)


def test_csv_escapes_formula_cells_with_leading_spaces():
    assert _csv_safe(' =HYPERLINK("https://example.com")').startswith("'")
