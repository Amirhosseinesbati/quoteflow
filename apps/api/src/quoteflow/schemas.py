from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DemoLogin(StrictModel):
    workspace: str = "arc-field-demo"
    role: Literal["admin", "operator", "viewer"] = "operator"


class Login(StrictModel):
    email: str
    password: str


class BriefCreate(StrictModel):
    source_type: Literal["paste", "form", "pasted_email", "public_form"] = "paste"
    text: str = Field(min_length=20, max_length=100000)
    company_name: str = Field(default="New client", max_length=200)
    contact_name: str = Field(default="", max_length=160)
    contact_email: str = Field(default="", max_length=250)


class ClarificationCreate(StrictModel):
    question: str = Field(min_length=5, max_length=2000)


class ClarificationEdit(StrictModel):
    question: str | None = None
    answer: str | None = None


class Answer(StrictModel):
    answer: str = Field(min_length=1, max_length=10000)


class QuoteLineEdit(StrictModel):
    service_id: str | None = None
    service_code: str | None = None
    service_name: str = Field(min_length=1, max_length=200)
    quantity: str = "1"
    unit_price: str | None = None
    assumption: str = Field(min_length=3, max_length=2000)


class VersionEdit(StrictModel):
    proposal: dict | None = None
    lines: list[QuoteLineEdit] | None = None
    discount_percent: str | None = None
    tax_percent: str | None = None
    contingency_percent: str | None = None
    label: str | None = None


class Decision(StrictModel):
    decision: Literal["approved", "rejected"]
    note: str = ""


class PortalDecision(StrictModel):
    decision: Literal["accepted", "declined", "revision_requested"]
    comment: str = ""


class ServiceEdit(StrictModel):
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=80)
    description: str = ""
    unit: str = "project"
    base_price: str
    active: bool = True
