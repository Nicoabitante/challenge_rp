from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Header, Router, Status

from invoices.exceptions import IdempotencyConflict
from invoices.models import Invoice
from invoices.schemas import ErrorOut, InvoiceCreateIn, InvoiceCreateOut, InvoiceDetailOut, InvoiceFailureOut
from invoices.services import invoice_to_create_out, invoice_to_detail_out, issue_invoice
from providers.exceptions import ProviderError, UnsupportedCountryError

router = Router(tags=["invoices"])


@router.post(
    "/invoices",
    response={
        200: InvoiceCreateOut,
        201: InvoiceCreateOut,
        400: ErrorOut,
        409: ErrorOut,
        502: InvoiceFailureOut,
    },
)
def create_invoice(request, payload: InvoiceCreateIn, idempotency_key: str = Header(..., alias="Idempotency-Key")):
    try:
        invoice, created = issue_invoice(payload, idempotency_key=idempotency_key)
    except UnsupportedCountryError as exc:
        return Status(400, {"detail": str(exc)})
    except IdempotencyConflict as exc:
        return Status(409, {"detail": str(exc)})
    except ProviderError as exc:
        failed_invoice = Invoice.objects.get(idempotency_key=idempotency_key)
        return Status(
            502,
            {
                "detail": str(exc),
                "invoice_id": failed_invoice.id,
                "status": failed_invoice.status,
                "provider_used": failed_invoice.provider_code,
            },
        )

    return Status(201 if created else 200, invoice_to_create_out(invoice))


@router.get(
    "/invoices/{invoice_id}",
    response={200: InvoiceDetailOut, 404: ErrorOut},
)
def get_invoice(request, invoice_id: UUID):
    invoice = get_object_or_404(Invoice.objects.prefetch_related("attempts"), id=invoice_id)
    return invoice_to_detail_out(invoice)
