from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scorecard", "0012_enforce_county_fk_non_null"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="senator",
            name="county",
        ),
    ]

