from django.db import migrations


def seed_methods(apps, schema_editor):
    PaymentMethodConfig = apps.get_model("donations", "PaymentMethodConfig")
    defaults = [
        {
            "method": "SSLCOMMERZ",
            "display_name": "SSLCommerz",
            "channel_kind": "ONLINE_HOSTED",
            "supports_one_time": True,
            "supports_recurring": False,
            "is_enabled": True,
            "display_order": 10,
        },
        {
            "method": "BKASH",
            "display_name": "bKash (via SSLCommerz hosted / not direct)",
            "channel_kind": "ONLINE_DIRECT",
            "hosted_via": "SSLCOMMERZ",
            "supports_one_time": False,
            "supports_recurring": False,
            "is_enabled": False,
            "display_order": 20,
        },
        {
            "method": "NAGAD",
            "display_name": "Nagad (via SSLCommerz hosted / not direct)",
            "channel_kind": "ONLINE_DIRECT",
            "hosted_via": "SSLCOMMERZ",
            "supports_one_time": False,
            "supports_recurring": False,
            "is_enabled": False,
            "display_order": 30,
        },
        {
            "method": "BANK_TRANSFER",
            "display_name": "Bank Transfer",
            "channel_kind": "MANUAL_OFFLINE",
            "supports_one_time": True,
            "supports_recurring": False,
            "is_enabled": True,
            "display_order": 40,
        },
        {
            "method": "CASH",
            "display_name": "Cash",
            "channel_kind": "MANUAL_OFFLINE",
            "supports_one_time": True,
            "supports_recurring": False,
            "is_enabled": True,
            "display_order": 50,
        },
        {
            "method": "OTHER",
            "display_name": "Other",
            "channel_kind": "MANUAL_OFFLINE",
            "supports_one_time": True,
            "supports_recurring": False,
            "is_enabled": True,
            "display_order": 60,
        },
    ]
    for row in defaults:
        PaymentMethodConfig.objects.update_or_create(
            method=row["method"],
            defaults=row,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("donations", "0005_batch2_membership_fees"),
    ]

    operations = [
        migrations.RunPython(seed_methods, noop),
    ]
