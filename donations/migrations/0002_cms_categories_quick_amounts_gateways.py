import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="donationcategory",
            options={
                "ordering": ["display_order", "name_en"],
                "verbose_name_plural": "donation categories",
            },
        ),
        migrations.AddField(
            model_name="donationcategory",
            name="display_order",
            field=models.PositiveIntegerField(
                db_index=True,
                default=0,
                help_text="Lower numbers appear first on the donation page.",
            ),
        ),
        migrations.AddField(
            model_name="donationcategory",
            name="icon",
            field=models.CharField(
                blank=True,
                default="bi-heart-fill",
                help_text="Bootstrap Icons class, e.g. bi-heart-fill, bi-book, bi-droplet.",
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name="donationcategory",
            name="is_default",
            field=models.BooleanField(
                default=False,
                help_text="Pre-selected in the donation form. Only one category can be default.",
                verbose_name="Default category",
            ),
        ),
        migrations.AlterField(
            model_name="donationcategory",
            name="description_bn",
            field=models.TextField(blank=True, null=True, verbose_name="Description (Bangla)"),
        ),
        migrations.AlterField(
            model_name="donationcategory",
            name="description_en",
            field=models.TextField(blank=True, null=True, verbose_name="Description (English)"),
        ),
        migrations.AlterField(
            model_name="donationcategory",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Optional cover image for the category card.",
                null=True,
                upload_to="donations/categories/",
            ),
        ),
        migrations.AlterField(
            model_name="donationcategory",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Active"),
        ),
        migrations.AlterField(
            model_name="donationcategory",
            name="is_featured",
            field=models.BooleanField(
                default=False,
                help_text="Highlight this category visually on the donation page.",
            ),
        ),
        migrations.AlterField(
            model_name="donationcategory",
            name="name_bn",
            field=models.CharField(max_length=200, verbose_name="Name (Bangla)"),
        ),
        migrations.AlterField(
            model_name="donationcategory",
            name="name_en",
            field=models.CharField(max_length=200, verbose_name="Name (English)"),
        ),
        migrations.AddIndex(
            model_name="donationcategory",
            index=models.Index(fields=["display_order"], name="donations_d_display_7a0c1a_idx"),
        ),
        migrations.AddField(
            model_name="transaction",
            name="gateway",
            field=models.CharField(
                choices=[
                    ("SSLCOMMERZ", "SSLCommerz"),
                    ("BKASH", "bKash"),
                    ("NAGAD", "Nagad"),
                    ("ROCKET", "Rocket"),
                    ("BANK_TRANSFER", "Bank Transfer"),
                    ("CASH", "Cash"),
                    ("OTHER", "Other"),
                ],
                db_index=True,
                default="SSLCOMMERZ",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("SSLCOMMERZ", "SSLCommerz"),
                    ("BKASH", "bKash"),
                    ("NAGAD", "Nagad"),
                    ("ROCKET", "Rocket"),
                    ("BANK_TRANSFER", "Bank Transfer"),
                    ("CASH", "Cash"),
                    ("OTHER", "Other"),
                ],
                default="SSLCOMMERZ",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="donationsubscription",
            name="payment_gateway",
            field=models.CharField(
                choices=[
                    ("SSLCOMMERZ", "SSLCommerz"),
                    ("BKASH", "bKash"),
                    ("NAGAD", "Nagad"),
                    ("ROCKET", "Rocket"),
                    ("BANK_TRANSFER", "Bank Transfer"),
                    ("CASH", "Cash"),
                    ("OTHER", "Other"),
                ],
                default="SSLCOMMERZ",
                max_length=50,
            ),
        ),
        migrations.CreateModel(
            name="DonationQuickAmount",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "amount",
                    models.FloatField(help_text="Suggested amount in BDT."),
                ),
                (
                    "label_en",
                    models.CharField(
                        blank=True,
                        help_text="Optional English chip label (defaults to the amount).",
                        max_length=80,
                    ),
                ),
                (
                    "label_bn",
                    models.CharField(
                        blank=True,
                        help_text="Optional Bangla chip label (defaults to the amount).",
                        max_length=80,
                    ),
                ),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quick_amounts",
                        to="donations.donationcategory",
                    ),
                ),
            ],
            options={
                "verbose_name": "Quick donation amount",
                "verbose_name_plural": "Quick donation amounts",
                "ordering": ["display_order", "amount"],
                "indexes": [
                    models.Index(
                        fields=["category", "is_active"],
                        name="donations_d_categor_9f2b1c_idx",
                    ),
                ],
            },
        ),
    ]
