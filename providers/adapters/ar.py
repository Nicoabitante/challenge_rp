from providers.base import BillingProvider
from providers.types import ProviderInvoiceRequest, ProviderInvoiceResult


class ProviderAR(BillingProvider):
    code = "provider_ar"
    name = "Proveedor AR"
    country_code = "AR"
    timeout_seconds = 2.0
    max_retries = 2
    backoff_seconds = 0.1

    def build_payload(self, request: ProviderInvoiceRequest) -> dict:
        return {
            "request_id": request.idempotency_key,
            "invoice": {
                "id": request.invoice_id,
                "entity": request.entity_id,
                "amount": str(request.amount),
                "currency": request.currency,
                "type": "B",
            },
        }

    def issue(self, payload: dict) -> ProviderInvoiceResult:
        reference = f"AR-{payload['request_id'][:12]}"
        return ProviderInvoiceResult(
            external_reference=reference,
            raw_response={
                "cae": reference,
                "result": "approved",
            },
        )
