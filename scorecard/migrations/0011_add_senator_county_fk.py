from django.db import migrations, models


def populate_senator_county_fk(apps, schema_editor):
    Senator = apps.get_model("scorecard", "Senator")
    County = apps.get_model("scorecard", "County")

    counties = list(County.objects.all())
    if not counties:
        return

    def match_county(county_name: str):
        """Best-effort match of a raw senator.county string to a County."""
        if not county_name:
            return None
        raw = county_name.strip().lower()
        raw = raw.replace(" county", "").replace(" city", "").strip()
        raw_norm = raw.replace(" ", "-").replace("'", "")

        # Exact name match first
        for c in counties:
            name_lower = c.name.lower()
            if raw == name_lower or raw == name_lower.replace(" county", "").replace(" city", "").strip():
                return c

        # Fuzzy contains / normalized match
        for c in counties:
            name_lower = c.name.lower()
            name_norm = name_lower.replace(" ", "-").replace("'", "")
            if name_lower in raw or raw in name_lower:
                return c
            if name_norm in raw_norm or raw_norm in name_norm:
                return c

        # First-word heuristic (e.g., "Homa" vs "Homa Bay")
        for c in counties:
            name_lower = c.name.lower()
            if raw.split()[0] == name_lower.split()[0]:
                return c

        return None

    for senator in Senator.objects.filter(county_fk__isnull=True):
        match = match_county(senator.county or "")
        if match:
            senator.county_fk_id = match.id
            senator.save(update_fields=["county_fk"])


class Migration(migrations.Migration):

    dependencies = [
        ("scorecard", "0010_populate_county_descriptions"),
    ]

    operations = [
        migrations.AddField(
            model_name="senator",
            name="county_fk",
            field=models.ForeignKey(
                to="scorecard.county",
                null=True,
                blank=True,
                on_delete=models.SET_NULL,
                related_name="senators",
                help_text="Linked county record, where applicable",
            ),
        ),
        migrations.RunPython(populate_senator_county_fk, migrations.RunPython.noop),
    ]

