from providers.base import BillingProvider
from providers.exceptions import ProviderPermanentError, ProviderTransientError
from providers.http_client import post_json
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
        response = post_json(self.endpoint_url, payload, timeout_seconds=self.timeout_seconds)
        if response.status_code >= 500:
            raise ProviderTransientError(f"{self.name} returned {response.status_code}.")
        if response.status_code >= 400:
            raise ProviderPermanentError(f"{self.name} rejected invoice: {response.body}")

        reference = response.body["notaFiscalId"]
        return ProviderInvoiceResult(
            external_reference=reference,
            raw_response=response.body,
        )
