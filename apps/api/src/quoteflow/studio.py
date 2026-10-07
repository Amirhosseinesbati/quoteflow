"""Workspace-owned defaults and immutable document identity for each quote version."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from sqlalchemy.orm import Session

from .config import get_settings
from .models import WorkspacePreference
from .pricing import PricingError, percent
from .schemas import StrictModel


class StudioSettings(StrictModel):
    studio_name: str = Field(default="Arc & Field Studio", min_length=2, max_length=100)
    accent_color: str = Field(default="#b65e4b", pattern=r"^#[0-9a-fA-F]{6}$")
    currency: Literal["USD", "EUR", "GBP", "CAD", "AUD", "CHF"] = "USD"
    tax_label: str = Field(default="Tax", min_length=1, max_length=24)
    default_tax_percent: str = "0.00"
    default_contingency_percent: str = "0.00"
    approval_discount_threshold: str = "10.00"
    title_template: str = Field(default="Making room for what's next.", min_length=3, max_length=160)
    summary_template: str = Field(
        default="{studio} proposes the {package} engagement for {client}, based on the supplied brief and the scope shown below.",
        min_length=10, max_length=1500,
    )
    terms: str = Field(
        default="Sample terms: work starts after a separate services agreement and agreed deposit. This proposal is not legal advice or a certified electronic signature.",
        min_length=10, max_length=4000,
    )
    footer_note: str = Field(default="Prepared with care", max_length=160)

    @field_validator("studio_name", "tax_label", "title_template", "summary_template", "terms")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value.strip()

    @field_validator("studio_name", "tax_label")
    @classmethod
    def single_line(cls, value: str) -> str:
        if any(ord(character) < 32 for character in value):
            raise ValueError("Use a single line without control characters")
        return value

    @field_validator("default_tax_percent", "default_contingency_percent", "approval_discount_threshold")
    @classmethod
    def percentage(cls, value: str) -> str:
        try:
            number = percent(value, "percentage")
        except PricingError as exc:
            raise ValueError(str(exc)) from exc
        return f"{number:.2f}"


class StudioUpdate(StrictModel):
    settings: StudioSettings
    expected_revision: int = Field(ge=0)


def studio_settings(db: Session, workspace_id: str) -> tuple[StudioSettings, int]:
    record = db.get(WorkspacePreference, workspace_id)
    if record is not None:
        return StudioSettings.model_validate(record.settings), record.revision
    config = get_settings()
    return StudioSettings(
        default_tax_percent=config.default_tax_percent,
        default_contingency_percent=config.default_contingency_percent,
        approval_discount_threshold=config.approval_discount_threshold,
    ), 0


def document_snapshot(settings: StudioSettings) -> dict:
    return {**settings.model_dump(), "synthetic": get_settings().mode.upper() == "DEMO"}


def document_settings(proposal: dict) -> dict:
    # Old proposals retain their original demo identity; never apply today's branding to them.
    return {**StudioSettings().model_dump(), "synthetic": True, **proposal.get("_document", {})}


def template_text(template: str, *, studio: str, client: str, package: str) -> str:
    for key, value in {"studio": studio, "client": client, "package": package}.items():
        template = template.replace("{" + key + "}", value)
    return template
