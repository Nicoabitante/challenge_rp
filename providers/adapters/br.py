from providers.base import BillingProvider
from providers.types import ProviderInvoiceRequest, ProviderInvoiceResult


class ProviderBR(BillingProvider):
    code = "provider_br"
    name = "Proveedor BR"
    country_code = "BR"
    timeout_seconds = 2.0
    max_retries = 2
    backoff_seconds = 0.1

    def build_payload(self, request: ProviderInvoiceRequest) -> dict:
        return {
            "correlationId": request.idempotency_key,
            "customerId": request.entity_id,
            "total": {
                "value": str(request.amount),
                "currency": request.currency,
            },
            "metadata": {
                "invoiceId": request.invoice_id,
                "country": request.country_code,
            },
        }

    def issue(self, payload: dict) -> ProviderInvoiceResult:
        reference = f"BR-{payload['correlationId'][:12]}"
        return ProviderInvoiceResult(
            external_reference=reference,
            raw_response={
                "notaFiscalId": reference,
                "status": "authorized",
            },
        )
