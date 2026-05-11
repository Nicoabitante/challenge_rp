from __future__ import annotations

import concurrent.futures
import hashlib
import json
import time
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from invoices.exceptions import IdempotencyConflict
from invoices.models import AttemptStatus, Invoice, InvoiceAttempt, InvoiceStatus
from invoices.schemas import InvoiceCreateIn
from providers.exceptions import (
    ProviderError,
    ProviderPermanentError,
    ProviderTimeoutError,
    ProviderTransientError,
)
from providers.registry import get_provider_for_country
from providers.types import ProviderInvoiceRequest, ProviderInvoiceResult


def issue_invoice(
    payload: InvoiceCreateIn,
    *,
    idempotency_key: str,
) -> tuple[Invoice, bool]:
    request_hash = _hash_request(payload)
    provider = get_provider_for_country(payload.country_code)

    invoice, created = _get_or_create_invoice(payload, idempotency_key, request_hash, provider.code)
    if not created:
        if invoice.request_hash != request_hash:
            raise IdempotencyConflict("Idempotency-Key was already used with a different payload.")
        return invoice, False

    provider_request = ProviderInvoiceRequest(
        invoice_id=str(invoice.id),
        entity_id=invoice.entity_id,
        amount=invoice.amount,
        currency=invoice.currency,
        country_code=invoice.country_code,
        idempotency_key=invoice.idempotency_key,
    )
    provider_payload = provider.build_payload(provider_request)

    try:
        result = _issue_with_retries(invoice, provider, provider_payload)
    except ProviderError as exc:
        invoice.status = InvoiceStatus.FAILED
        invoice.failure_reason = str(exc)
        invoice.save(update_fields=["status", "failure_reason", "updated_at"])
        raise

    invoice.status = InvoiceStatus.ISSUED
    invoice.external_reference = result.external_reference
    invoice.issued_at = timezone.now()
    invoice.save(update_fields=["status", "external_reference", "issued_at", "updated_at"])
    return invoice, True


def _get_or_create_invoice(
    payload: InvoiceCreateIn,
    idempotency_key: str,
    request_hash: str,
    provider_code: str,
) -> tuple[Invoice, bool]:
    try:
        with transaction.atomic():
            return (
                Invoice.objects.create(
                    entity_id=payload.entity_id,
                    amount=payload.amount,
                    currency=payload.currency.upper(),
                    country_code=payload.country_code.upper(),
                    provider_code=provider_code,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                ),
                True,
            )
    except IntegrityError:
        return Invoice.objects.get(idempotency_key=idempotency_key), False


def _issue_with_retries(provider_invoice: Invoice, provider, payload: dict) -> ProviderInvoiceResult:
    max_attempts = provider.max_retries + 1
    last_error: ProviderError | None = None

    for attempt_number in range(1, max_attempts + 1):
        started_at = timezone.now()
        started = time.monotonic()

        try:
            result = _call_provider_with_timeout(provider, payload)
        except ProviderTimeoutError as exc:
            last_error = exc
            _record_attempt(provider_invoice, attempt_number, provider.code, payload, None, AttemptStatus.TIMEOUT, exc, started_at, started)
        except ProviderTransientError as exc:
            last_error = exc
            _record_attempt(provider_invoice, attempt_number, provider.code, payload, None, AttemptStatus.TRANSIENT_ERROR, exc, started_at, started)
        except ProviderPermanentError as exc:
            _record_attempt(provider_invoice, attempt_number, provider.code, payload, None, AttemptStatus.FAILED, exc, started_at, started)
            raise
        else:
            _record_attempt(provider_invoice, attempt_number, provider.code, payload, result.raw_response, AttemptStatus.SUCCESS, None, started_at, started)
            return result

        if attempt_number < max_attempts:
            time.sleep(provider.backoff_seconds * (2 ** (attempt_number - 1)))

    raise last_error or ProviderTransientError("Provider failed after retries.")


def _call_provider_with_timeout(provider, payload: dict) -> ProviderInvoiceResult:
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(provider.issue, payload)
    try:
        return future.result(timeout=provider.timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise ProviderTimeoutError(f"Provider {provider.code} timed out.") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _record_attempt(
    invoice: Invoice,
    attempt_number: int,
    provider_code: str,
    request_payload: dict,
    response_payload: dict | None,
    status: str,
    error: Exception | None,
    started_at,
    started: float,
) -> None:
    finished_at = timezone.now()
    duration_ms = int((time.monotonic() - started) * 1000)
    InvoiceAttempt.objects.create(
        invoice=invoice,
        attempt_number=attempt_number,
        provider_code=provider_code,
        request_payload=request_payload,
        response_payload=response_payload,
        status=status,
        error_message=str(error) if error else "",
        duration_ms=duration_ms,
        started_at=started_at,
        finished_at=finished_at,
    )


def _hash_request(payload: InvoiceCreateIn) -> str:
    normalized = {
        "entity_id": payload.entity_id,
        "amount": str(Decimal(payload.amount).quantize(Decimal("0.01"))),
        "currency": payload.currency.upper(),
        "country_code": payload.country_code.upper(),
    }
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def invoice_to_create_out(invoice: Invoice) -> dict:
    return {
        "invoice_id": invoice.id,
        "status": invoice.status,
        "provider_used": invoice.provider_code,
        "external_reference": invoice.external_reference,
    }


def invoice_to_detail_out(invoice: Invoice) -> dict:
    data = invoice_to_create_out(invoice)
    data.update(
        {
            "entity_id": invoice.entity_id,
            "amount": invoice.amount,
            "currency": invoice.currency,
            "country_code": invoice.country_code,
            "failure_reason": invoice.failure_reason,
            "created_at": invoice.created_at.isoformat(),
            "updated_at": invoice.updated_at.isoformat(),
            "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
            "attempts": [
                {
                    "attempt_number": attempt.attempt_number,
                    "provider_code": attempt.provider_code,
                    "request_payload": attempt.request_payload,
                    "response_payload": attempt.response_payload,
                    "status": attempt.status,
                    "error_message": attempt.error_message,
                    "duration_ms": attempt.duration_ms,
                    "started_at": attempt.started_at.isoformat(),
                    "finished_at": attempt.finished_at.isoformat(),
                }
                for attempt in invoice.attempts.all()
            ],
        }
    )
    return data
