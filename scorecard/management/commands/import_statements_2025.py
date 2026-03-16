"""
Imports senators' formal statements from a CSV exported from the official
Statements Tracker PDF (e.g. "Statements Tracker - Updated as at 20.11.2025").

Usage:
    python manage.py import_statements_2025 --csv data/statements_tracker_2025.csv

Expected CSV columns (case-insensitive, extra columns are ignored):
    - senator_name  (required)
    - statements    (required, integer)

You can export these columns from the PDF using Tabula/Acrobat and save as UTF‑8 CSV.
"""

import csv
import os
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from scorecard.models import Senator, ParliamentaryPerformance


def _normalize_name(name: str) -> str:
    """Uppercase, strip titles, and collapse spaces to normalize names."""
    if not name:
        return ""
    name = name.replace(".", " ")
    # Strip common titles
    for prefix in ("HON", "SEN", "DR", "ENG", "PROF", "MR", "MRS", "MS"):
        name = name.replace(prefix + " ", " ")
    cleaned = " ".join(name.upper().split())
    return cleaned


class Command(BaseCommand):
    help = "Import 2025 statements counts from an exported Statements Tracker CSV into ParliamentaryPerformance."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            dest="csv_path",
            default="data/statements_tracker_2025.csv",
            help="Path to CSV exported from Statements Tracker PDF.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        if not os.path.exists(csv_path):
            raise CommandError(f"CSV file not found: {csv_path}")

        self.stdout.write(self.style.NOTICE(f"Reading statements data from {csv_path!r}"))

        rows = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # Normalize field names
            field_map = {name.lower().strip(): name for name in reader.fieldnames or []}
            name_field = field_map.get("senator_name") or field_map.get("name") or field_map.get("senator")
            count_field = field_map.get("statements") or field_map.get("count") or field_map.get("no_of_statements")
            if not name_field or not count_field:
                raise CommandError(
                    "CSV must contain 'senator_name' and 'statements' columns (case-insensitive). "
                    f"Found columns: {reader.fieldnames!r}"
                )
            for row in reader:
                raw_name = (row.get(name_field) or "").strip()
                if not raw_name:
                    continue
                try:
                    cnt = int((row.get(count_field) or "0").replace(",", "").strip())
                except ValueError:
                    cnt = 0
                rows.append((raw_name, cnt))

        if not rows:
            self.stdout.write(self.style.WARNING("No rows found in CSV after parsing. Nothing to do."))
            return

        # Build senator name index
        senators = list(Senator.objects.all().select_related("perf"))
        index = {_normalize_name(s.name): s for s in senators}

        # Manual aliases for names that differ between tracker and DB
        # Extend this dict as needed after first run.
        NAME_ALIASES = {
            # "TRACKER NAME": "senator_id"
            # Example:
            # "AARON KIPKIRUI CHERARGEI": "samson-kiprotich-cherargei",
        }
        alias_index = {
            _normalize_name(k): next((s for s in senators if s.senator_id == v), None)
            for k, v in NAME_ALIASES.items()
        }

        updated = 0
        unmatched = []
        duplicates = defaultdict(list)

        for raw_name, cnt in rows:
            norm = _normalize_name(raw_name)
            senator = index.get(norm) or alias_index.get(norm)
            if not senator:
                unmatched.append((raw_name, cnt))
                continue

            # Track duplicates in CSV (multiple rows per senator)
            duplicates[senator.senator_id].append(cnt)

        # Aggregate per senator (sum counts if duplicated)
        for sid, counts in duplicates.items():
            senator = next(s for s in senators if s.senator_id == sid)
            total_statements = sum(counts)
            perf, _ = ParliamentaryPerformance.objects.get_or_create(senator=senator)
            perf.statements_2025 = total_statements
            perf.statements_total = total_statements
            perf.save(update_fields=["statements_2025", "statements_total"])
            updated += 1
            self.stdout.write(f"Updated {senator.name}: {total_statements} statements (2025)")

        self.stdout.write(self.style.SUCCESS(f"\nUpdated statements for {updated} senators."))

        if unmatched:
            self.stdout.write(self.style.WARNING("\nUnmatched rows (add to NAME_ALIASES or fix CSV):"))
            for name, cnt in unmatched:
                self.stdout.write(f"  - {name!r}: {cnt}")

