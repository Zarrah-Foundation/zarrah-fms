from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0003_replace_magic_validators"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="memberapplication",
            name="membership_category",
        ),
    ]
