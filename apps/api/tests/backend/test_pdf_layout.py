"""Focused regression for approved line order and long-row pagination."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from quoteflow.db import Base
from quoteflow.models import QuoteLine, QuoteVersion
from quoteflow.pdf import render_proposal_pdf


def test_pdf_preserves_line_order_and_complete_long_assumption_across_pages():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        version = QuoteVersion(
            quote_id="quote-layout",
            number=4,
            label="Recommended",
            status="approved",
            catalog_version_id="catalog-layout",
            content_hash="a" * 64,
            proposal={"executive_summary": "A considered proposal.", "scope": "Scope detail " * 280},
            subtotal=Decimal("1500.00"),
            discount_percent=Decimal("10.00"),
            discount_amount=Decimal("150.00"),
            contingency_percent=Decimal("0.00"),
            contingency_amount=Decimal("0.00"),
            tax_percent=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total=Decimal("1350.00"),
        )
        session.add(version)
        session.flush()
        session.add_all(
            [
                QuoteLine(
                    version_id=version.id,
                    position=0,
                    service_code="zeta",
                    service_name="Zeta " + "long service name " * 9,
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("1000.00"),
                    line_total=Decimal("1000.00"),
                    assumption="First approved item.",
                ),
                QuoteLine(
                    version_id=version.id,
                    position=1,
                    service_code="alpha",
                    service_name="Alpha service",
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("500.00"),
                    line_total=Decimal("500.00"),
                    assumption="\n".join(f"Checkpoint {index:03}" for index in range(120)),
                ),
            ]
        )
        session.commit()
        session.expire_all()
        approved = session.get(QuoteVersion, version.id)
        assert [line.service_code for line in approved.lines] == ["zeta", "alpha"]
        pdf = render_proposal_pdf(approved, client_name="A very long client name " * 6, brief_reference="brief-layout")
    pages = [page.extract_text() for page in PdfReader(BytesIO(pdf)).pages]
    text = "\n".join(pages)
    assert len(pages) >= 2
    assert text.index("Zeta") < text.index("Alpha service")
    assert "Checkpoint 000" in text and "Checkpoint 119" in text
    assert all("Service" in page for page in pages if "Investment" in page)
    assert any(all(label in page for label in ("Subtotal", "Discount", "Contingency", "Tax", "Total")) for page in pages)
