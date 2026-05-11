import uuid

from django.db import models


class InvoiceStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ISSUED = "issued", "Issued"
    FAILED = "failed", "Failed"


class AttemptStatus(models.TextChoices):
    SUCCESS = "success", "Success"
    TRANSIENT_ERROR = "transient_error", "Transient error"
    TIMEOUT = "timeout", "Timeout"
    FAILED = "failed", "Failed"


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3)
    country_code = models.CharField(max_length=2)
    status = models.CharField(
        max_length=16,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.PENDING,
    )
    provider_code = models.CharField(max_length=64)
    external_reference = models.CharField(max_length=255, blank=True)
    idempotency_key = models.CharField(max_length=255, unique=True)
    request_hash = models.CharField(max_length=64)
    failure_reason = models.TextField(blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["country_code", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.id} ({self.status})"


class InvoiceAttempt(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        related_name="attempts",
        on_delete=models.CASCADE,
    )
    attempt_number = models.PositiveIntegerField()
    provider_code = models.CharField(max_length=64)
    request_payload = models.JSONField()
    response_payload = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=AttemptStatus.choices)
    error_message = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField()

    class Meta:
        ordering = ["attempt_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["invoice", "attempt_number"],
                name="unique_invoice_attempt_number",
            )
        ]

    def __str__(self) -> str:
        return f"{self.invoice_id} attempt {self.attempt_number}"
