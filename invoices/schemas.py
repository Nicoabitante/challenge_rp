from decimal import Decimal
from typing import Literal
from uuid import UUID

from ninja import Schema
from pydantic import Field


class InvoiceCreateIn(Schema):
    entity_id: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    country_code: str = Field(min_length=2, max_length=2)


class InvoiceCreateOut(Schema):
    invoice_id: UUID
    status: Literal["issued", "pending", "failed"]
    provider_used: str
    external_reference: str


class InvoiceAttemptOut(Schema):
    attempt_number: int
    provider_code: str
    request_payload: dict
    response_payload: dict | None
    status: str
    error_message: str
    duration_ms: int
    started_at: str
    finished_at: str


class InvoiceDetailOut(InvoiceCreateOut):
    entity_id: str
    amount: Decimal
    currency: str
    country_code: str
    failure_reason: str
    created_at: str
    updated_at: str
    issued_at: str | None
    attempts: list[InvoiceAttemptOut]


class ErrorOut(Schema):
    detail: str


class InvoiceFailureOut(ErrorOut):
    invoice_id: UUID
    status: Literal["failed"]
    provider_used: str
