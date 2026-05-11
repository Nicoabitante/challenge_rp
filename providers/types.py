from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProviderInvoiceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    invoice_id: str
    entity_id: str
    amount: Decimal
    currency: str
    country_code: str
    idempotency_key: str


class ProviderInvoiceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    external_reference: str
    raw_response: dict[str, Any]
