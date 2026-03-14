from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scorecard", "0011_add_senator_county_fk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="senator",
            name="county_fk",
            field=models.ForeignKey(
                to="scorecard.county",
                on_delete=models.PROTECT,
                null=False,
                blank=False,
                related_name="senators",
                help_text="Linked county record, where applicable",
            ),
        ),
    ]

