# Generated manually for the billing challenge baseline.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("entity_id", models.CharField(max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(max_length=3)),
                ("country_code", models.CharField(max_length=2)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("issued", "Issued"), ("failed", "Failed")], default="pending", max_length=16)),
                ("provider_code", models.CharField(max_length=64)),
                ("external_reference", models.CharField(blank=True, max_length=255)),
                ("idempotency_key", models.CharField(max_length=255, unique=True)),
                ("request_hash", models.CharField(max_length=64)),
                ("failure_reason", models.TextField(blank=True)),
                ("issued_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="InvoiceAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempt_number", models.PositiveIntegerField()),
                ("provider_code", models.CharField(max_length=64)),
                ("request_payload", models.JSONField()),
                ("response_payload", models.JSONField(blank=True, null=True)),
                ("status", models.CharField(choices=[("success", "Success"), ("transient_error", "Transient error"), ("timeout", "Timeout"), ("failed", "Failed")], max_length=32)),
                ("error_message", models.TextField(blank=True)),
                ("duration_ms", models.PositiveIntegerField()),
                ("started_at", models.DateTimeField()),
                ("finished_at", models.DateTimeField()),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="invoices.invoice")),
            ],
            options={
                "ordering": ["attempt_number"],
            },
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["country_code", "status"], name="invoices_in_country_48765f_idx"),
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["created_at"], name="invoices_in_created_09931a_idx"),
        ),
        migrations.AddConstraint(
            model_name="invoiceattempt",
            constraint=models.UniqueConstraint(fields=("invoice", "attempt_number"), name="unique_invoice_attempt_number"),
        ),
    ]
