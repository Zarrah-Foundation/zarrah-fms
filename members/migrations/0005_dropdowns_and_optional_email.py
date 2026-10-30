from django.db import migrations, models


BLOOD_GROUP_CHOICES = [
    ("A+", "A+"),
    ("A-", "A-"),
    ("B+", "B+"),
    ("B-", "B-"),
    ("AB+", "AB+"),
    ("AB-", "AB-"),
    ("O+", "O+"),
    ("O-", "O-"),
]

RELIGION_CHOICES = [
    ("ISLAM", "Islam"),
    ("HINDU", "Hindu"),
    ("CHRISTIAN", "Christian"),
    ("BUDDHIST", "Buddhist"),
    ("OTHER", "Other"),
]

GENDER_CHOICES = [
    ("MALE", "Male"),
    ("FEMALE", "Female"),
    ("OTHER", "Hijra"),
]

MARITAL_STATUS_CHOICES = [
    ("SINGLE", "Single"),
    ("MARRIED", "Married"),
    ("DIVORCED", "Divorced"),
    ("WIDOWED", "Widowed"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0004_remove_membership_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="member",
            name="gender",
            field=models.CharField(blank=True, choices=GENDER_CHOICES, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name="member",
            name="blood_group",
            field=models.CharField(blank=True, choices=BLOOD_GROUP_CHOICES, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="gender",
            field=models.CharField(choices=GENDER_CHOICES, max_length=10),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="blood_group",
            field=models.CharField(blank=True, choices=BLOOD_GROUP_CHOICES, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="religion",
            field=models.CharField(blank=True, choices=RELIGION_CHOICES, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="marital_status",
            field=models.CharField(choices=MARITAL_STATUS_CHOICES, default="SINGLE", max_length=20),
        ),
    ]
