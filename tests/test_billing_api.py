import pytest

from invoices.models import AttemptStatus, Invoice, InvoiceAttempt, InvoiceStatus
from providers.exceptions import ProviderTimeoutError
from providers.http_client import JsonResponse
from providers.types import ProviderInvoiceResult


@pytest.fixture(autouse=True)
def provider_http_mocks(monkeypatch):
    def post_ar(url, payload, *, timeout_seconds):
        return JsonResponse(
            status_code=201,
            body={
                "cae": f"AR-{payload['request_id'][:12]}",
                "result": "approved",
            },
        )

    def post_br(url, payload, *, timeout_seconds):
        return JsonResponse(
            status_code=201,
            body={
                "notaFiscalId": f"BR-{payload['correlationId'][:12]}",
                "status": "authorized",
            },
        )

    monkeypatch.setattr("providers.adapters.ar.post_json", post_ar)
    monkeypatch.setattr("providers.adapters.br.post_json", post_br)


@pytest.mark.django_db
def test_list_providers(client):
    response = client.get("/providers")

    assert response.status_code == 200
    assert response.json() == [
        {
            "country_code": "AR",
            "provider_code": "provider_ar",
            "name": "Proveedor AR",
            "timeout_seconds": 2.0,
            "max_retries": 2,
        },
        {
            "country_code": "BR",
            "provider_code": "provider_br",
            "name": "Proveedor BR",
            "timeout_seconds": 2.0,
            "max_retries": 2,
        },
    ]


@pytest.mark.django_db
def test_issue_invoice_successfully(client):
    response = client.post(
        "/invoices",
        {
            "entity_id": "customer-1",
            "amount": "1500.00",
            "currency": "ARS",
            "country_code": "AR",
        },
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-1"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "issued"
    assert body["provider_used"] == "provider_ar"
    assert body["external_reference"] == "AR-invoice-key-"
    assert Invoice.objects.count() == 1
    assert InvoiceAttempt.objects.count() == 1


@pytest.mark.django_db
def test_get_invoice_returns_audit_trail(client):
    created = client.post(
        "/invoices",
        {
            "entity_id": "customer-2",
            "amount": "10.50",
            "currency": "BRL",
            "country_code": "BR",
        },
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-2"},
    )

    response = client.get(f"/invoices/{created.json()['invoice_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "issued"
    assert body["provider_used"] == "provider_br"
    assert body["attempts"][0]["status"] == "success"
    assert body["attempts"][0]["request_payload"]["correlationId"] == "invoice-key-2"
    assert body["attempts"][0]["response_payload"]["status"] == "authorized"


@pytest.mark.django_db
def test_idempotency_key_reuses_existing_invoice(client):
    payload = {
        "entity_id": "customer-3",
        "amount": "99.99",
        "currency": "ARS",
        "country_code": "AR",
    }

    first_response = client.post(
        "/invoices",
        payload,
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-3"},
    )
    second_response = client.post(
        "/invoices",
        payload,
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-3"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert second_response.json()["invoice_id"] == first_response.json()["invoice_id"]
    assert Invoice.objects.count() == 1
    assert InvoiceAttempt.objects.count() == 1


@pytest.mark.django_db
def test_idempotency_key_with_different_payload_returns_conflict(client):
    headers = {"Idempotency-Key": "invoice-key-4"}
    response = client.post(
        "/invoices",
        {
            "entity_id": "customer-4",
            "amount": "10.00",
            "currency": "ARS",
            "country_code": "AR",
        },
        content_type="application/json",
        headers=headers,
    )
    conflict = client.post(
        "/invoices",
        {
            "entity_id": "customer-4",
            "amount": "11.00",
            "currency": "ARS",
            "country_code": "AR",
        },
        content_type="application/json",
        headers=headers,
    )

    assert response.status_code == 201
    assert conflict.status_code == 409


@pytest.mark.django_db
def test_provider_permanent_failure_marks_invoice_as_failed(client, monkeypatch):
    def post_ar(url, payload, *, timeout_seconds):
        return JsonResponse(status_code=422, body={"detail": "Invoice rejected"})

    monkeypatch.setattr("providers.adapters.ar.post_json", post_ar)

    response = client.post(
        "/invoices",
        {
            "entity_id": "customer-5",
            "amount": "25.00",
            "currency": "ARS",
            "country_code": "AR",
        },
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-5"},
    )

    invoice = Invoice.objects.get(idempotency_key="invoice-key-5")
    attempt = invoice.attempts.get()

    assert response.status_code == 502
    assert response.json()["status"] == "failed"
    assert invoice.status == InvoiceStatus.FAILED
    assert "rejected invoice" in invoice.failure_reason
    assert attempt.status == AttemptStatus.FAILED
    assert attempt.response_payload is None
    assert "Invoice rejected" in attempt.error_message


@pytest.mark.django_db
def test_transient_provider_failure_retries_then_issues_invoice(client, monkeypatch):
    responses = [
        JsonResponse(status_code=503, body={"detail": "temporary failure"}),
        JsonResponse(status_code=503, body={"detail": "temporary failure"}),
        JsonResponse(status_code=201, body={"cae": "AR-after-retry", "result": "approved"}),
    ]
    sleeps = []

    def post_ar(url, payload, *, timeout_seconds):
        return responses.pop(0)

    monkeypatch.setattr("providers.adapters.ar.post_json", post_ar)
    monkeypatch.setattr("invoices.services.time.sleep", sleeps.append)

    response = client.post(
        "/invoices",
        {
            "entity_id": "customer-6",
            "amount": "30.00",
            "currency": "ARS",
            "country_code": "AR",
        },
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-6"},
    )

    invoice = Invoice.objects.get(idempotency_key="invoice-key-6")
    attempts = list(invoice.attempts.all())

    assert response.status_code == 201
    assert response.json()["status"] == "issued"
    assert response.json()["external_reference"] == "AR-after-retry"
    assert invoice.status == InvoiceStatus.ISSUED
    assert [attempt.status for attempt in attempts] == [
        AttemptStatus.TRANSIENT_ERROR,
        AttemptStatus.TRANSIENT_ERROR,
        AttemptStatus.SUCCESS,
    ]
    assert sleeps == [0.1, 0.2]


@pytest.mark.django_db
def test_provider_timeouts_are_retried_and_finally_fail(client, monkeypatch):
    sleeps = []

    def post_ar(url, payload, *, timeout_seconds):
        raise ProviderTimeoutError("Provider request timed out.")

    monkeypatch.setattr("providers.adapters.ar.post_json", post_ar)
    monkeypatch.setattr("invoices.services.time.sleep", sleeps.append)

    response = client.post(
        "/invoices",
        {
            "entity_id": "customer-7",
            "amount": "35.00",
            "currency": "ARS",
            "country_code": "AR",
        },
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-7"},
    )

    invoice = Invoice.objects.get(idempotency_key="invoice-key-7")
    attempts = list(invoice.attempts.all())

    assert response.status_code == 502
    assert response.json()["status"] == "failed"
    assert invoice.status == InvoiceStatus.FAILED
    assert [attempt.status for attempt in attempts] == [
        AttemptStatus.TIMEOUT,
        AttemptStatus.TIMEOUT,
        AttemptStatus.TIMEOUT,
    ]
    assert sleeps == [0.1, 0.2]


@pytest.mark.django_db
def test_invoice_starts_as_pending_before_provider_finishes(client, monkeypatch):
    observed_statuses = []

    def call_provider(provider, payload):
        observed_statuses.append(Invoice.objects.get(idempotency_key="invoice-key-8").status)
        return ProviderInvoiceResult(
            external_reference="AR-pending-check",
            raw_response={"cae": "AR-pending-check", "result": "approved"},
        )

    monkeypatch.setattr("invoices.services._call_provider_with_timeout", call_provider)

    response = client.post(
        "/invoices",
        {
            "entity_id": "customer-8",
            "amount": "40.00",
            "currency": "ARS",
            "country_code": "AR",
        },
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-8"},
    )

    assert response.status_code == 201
    assert observed_statuses == [InvoiceStatus.PENDING]
    assert Invoice.objects.get(idempotency_key="invoice-key-8").status == InvoiceStatus.ISSUED
