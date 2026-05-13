from abc import ABC, abstractmethod

from django.conf import settings

from providers.types import ProviderInvoiceRequest, ProviderInvoiceResult


class BillingProvider(ABC):
    code: str
    name: str
    country_code: str
    timeout_seconds: float = 2.0
    max_retries: int = 2
    backoff_seconds: float = 0.1

    @property
    def endpoint_url(self) -> str:
        return settings.BILLING_PROVIDER_ENDPOINTS[self.code]

    @abstractmethod
    def build_payload(self, request: ProviderInvoiceRequest) -> dict:
        raise NotImplementedError

    @abstractmethod
    def issue(self, payload: dict) -> ProviderInvoiceResult:
        raise NotImplementedError
