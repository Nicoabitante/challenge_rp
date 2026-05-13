from decimal import Decimal

import pytest

from providers.adapters.ar import ProviderAR
from providers.adapters.br import ProviderBR
from providers.exceptions import ProviderPermanentError, ProviderTransientError
from providers.http_client import JsonResponse
from providers.types import ProviderInvoiceRequest


def test_provider_ar_posts_payload_and_maps_response(monkeypatch, settings):
    settings.BILLING_PROVIDER_ENDPOINTS = {"provider_ar": "http://provider-ar-mock:8080/invoices"}
    calls = []

    def fake_post_json(url, payload, *, timeout_seconds):
        calls.append((url, payload, timeout_seconds))
        return JsonResponse(status_code=201, body={"cae": "AR-123", "result": "approved"})

    monkeypatch.setattr("providers.adapters.ar.post_json", fake_post_json)

    provider = ProviderAR()
    payload = provider.build_payload(_provider_request(country_code="AR", currency="ARS"))
    result = provider.issue(payload)

    assert result.external_reference == "AR-123"
    assert result.raw_response == {"cae": "AR-123", "result": "approved"}
    assert calls == [("http://provider-ar-mock:8080/invoices", payload, 2.0)]


def test_provider_br_posts_payload_and_maps_response(monkeypatch, settings):
    settings.BILLING_PROVIDER_ENDPOINTS = {"provider_br": "http://provider-br-mock:8080/invoices"}
    calls = []

    def fake_post_json(url, payload, *, timeout_seconds):
        calls.append((url, payload, timeout_seconds))
        return JsonResponse(status_code=201, body={"notaFiscalId": "BR-123", "status": "authorized"})

    monkeypatch.setattr("providers.adapters.br.post_json", fake_post_json)

    provider = ProviderBR()
    payload = provider.build_payload(_provider_request(country_code="BR", currency="BRL"))
    result = provider.issue(payload)

    assert result.external_reference == "BR-123"
    assert result.raw_response == {"notaFiscalId": "BR-123", "status": "authorized"}
    assert calls == [("http://provider-br-mock:8080/invoices", payload, 2.0)]


def test_provider_transient_http_error_is_retryable(monkeypatch, settings):
    settings.BILLING_PROVIDER_ENDPOINTS = {"provider_ar": "http://provider-ar-mock:8080/invoices"}

    def fake_post_json(url, payload, *, timeout_seconds):
        return JsonResponse(status_code=503, body={"detail": "Temporary failure"})

    monkeypatch.setattr("providers.adapters.ar.post_json", fake_post_json)

    with pytest.raises(ProviderTransientError):
        ProviderAR().issue({"request_id": "key-1"})


def test_provider_permanent_http_error_is_not_retryable(monkeypatch, settings):
    settings.BILLING_PROVIDER_ENDPOINTS = {"provider_br": "http://provider-br-mock:8080/invoices"}

    def fake_post_json(url, payload, *, timeout_seconds):
        return JsonResponse(status_code=422, body={"detail": "Rejected"})

    monkeypatch.setattr("providers.adapters.br.post_json", fake_post_json)

    with pytest.raises(ProviderPermanentError):
        ProviderBR().issue({"correlationId": "key-1"})


def _provider_request(*, country_code: str, currency: str) -> ProviderInvoiceRequest:
    return ProviderInvoiceRequest(
        invoice_id="invoice-1",
        entity_id="customer-1",
        amount=Decimal("1500.00"),
        currency=currency,
        country_code=country_code,
        idempotency_key="invoice-key-1",
    )
