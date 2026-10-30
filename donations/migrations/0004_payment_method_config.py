import uuid

from django.db import migrations, models

PAYMENT_METHOD_CHOICES = [
    ("SSLCOMMERZ", "SSLCommerz"),
    ("BKASH", "bKash"),
    ("NAGAD", "Nagad"),
    ("ROCKET", "Rocket"),
    ("BANK_TRANSFER", "Bank Transfer"),
    ("CASH", "Cash"),
    ("OTHER", "Other"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0003_foundation_smtp_donation_receipts"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentMethodConfig",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("method", models.CharField(choices=PAYMENT_METHOD_CHOICES, max_length=20, unique=True)),
                ("display_name", models.CharField(blank=True, default="", max_length=100)),
                ("instructions_bn", models.TextField(blank=True, default="")),
                ("instructions_en", models.TextField(blank=True, default="")),
                ("account_details", models.CharField(blank=True, default="", help_text="Account/wallet number shown for manual payments.", max_length=255)),
                ("is_enabled", models.BooleanField(default=True)),
                ("display_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["display_order", "method"],
            },
        ),
    ]
