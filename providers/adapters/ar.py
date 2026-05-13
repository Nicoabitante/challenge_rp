from providers.base import BillingProvider
from providers.exceptions import ProviderPermanentError, ProviderTransientError
from providers.http_client import post_json
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
        response = post_json(self.endpoint_url, payload, timeout_seconds=self.timeout_seconds)
        if response.status_code >= 500:
            raise ProviderTransientError(f"{self.name} returned {response.status_code}.")
        if response.status_code >= 400:
            raise ProviderPermanentError(f"{self.name} rejected invoice: {response.body}")

        reference = response.body["cae"]
        return ProviderInvoiceResult(
            external_reference=reference,
            raw_response=response.body,
        )
