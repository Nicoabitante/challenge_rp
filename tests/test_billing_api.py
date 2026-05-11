import pytest

from invoices.models import Invoice, InvoiceAttempt


@pytest.mark.django_db
def test_list_providers(client):
    response = client.get("/api/providers")

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
        "/api/invoices",
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
        "/api/invoices",
        {
            "entity_id": "customer-2",
            "amount": "10.50",
            "currency": "BRL",
            "country_code": "BR",
        },
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-2"},
    )

    response = client.get(f"/api/invoices/{created.json()['invoice_id']}")

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
        "/api/invoices",
        payload,
        content_type="application/json",
        headers={"Idempotency-Key": "invoice-key-3"},
    )
    second_response = client.post(
        "/api/invoices",
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
        "/api/invoices",
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
        "/api/invoices",
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
