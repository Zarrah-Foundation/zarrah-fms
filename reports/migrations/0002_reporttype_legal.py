from django.db import migrations, models

REPORT_TYPE_CHOICES = [
    ("ANNUAL", "Annual"),
    ("AUDIT", "Audit"),
    ("FINANCIAL", "Financial"),
    ("ACTIVITY", "Activity"),
    ("CONSTITUTION", "Constitution"),
    ("POLICY", "Policy"),
    ("OTHER", "Other"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="report",
            name="type",
            field=models.CharField(choices=REPORT_TYPE_CHOICES, max_length=20),
        ),
    ]
