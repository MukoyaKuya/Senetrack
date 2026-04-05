"""
Apply bill counts from the authoritative bills_override.json to the database.

Usage:
    python manage.py sync_bills            # preview changes (dry-run)
    python manage.py sync_bills --apply    # apply changes and recalculate scores
"""
import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand

from scorecard.engine import HansardEngine, perf_to_engine_data
from scorecard.models import ParliamentaryPerformance, Senator

OVERRIDE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "bills_override.json"


class Command(BaseCommand):
    help = "Sync senator bill counts from scorecard/data/bills_override.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually write changes to the DB. Without this flag, runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        if not OVERRIDE_PATH.exists():
            self.stderr.write(self.style.ERROR(f"Override file not found: {OVERRIDE_PATH}"))
            return

        with open(OVERRIDE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("senators", [])
        self.stdout.write(f"Loaded {len(entries)} entries from {OVERRIDE_PATH.name}")
        self.stdout.write(f"Mode: {'APPLY' if apply else 'DRY-RUN (use --apply to write changes)'}\n")

        updated = 0
        skipped = 0
        not_found = 0
        unchanged = 0

        for entry in entries:
            sid = entry["senator_id"]
            new_sponsored = entry["sponsored_bills"]
            new_passed = entry["passed_bills"]

            try:
                senator = Senator.objects.select_related("perf").get(senator_id=sid)
            except Senator.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  NOT FOUND: {sid} ({entry.get('name', '?')})"))
                not_found += 1
                continue

            perf = getattr(senator, "perf", None)
            if perf is None:
                self.stdout.write(self.style.WARNING(f"  NO PERF: {senator.name} ({sid})"))
                skipped += 1
                continue

            if perf.sponsored_bills == new_sponsored and perf.passed_bills == new_passed:
                unchanged += 1
                continue

            self.stdout.write(
                f"  {senator.name}: "
                f"sponsored {perf.sponsored_bills} -> {new_sponsored}, "
                f"passed {perf.passed_bills} -> {new_passed}"
            )

            if apply:
                perf.sponsored_bills = new_sponsored
                perf.passed_bills = new_passed
                perf.save(update_fields=["sponsored_bills", "passed_bills"])

                # Recalculate score
                engine_data = perf_to_engine_data(perf)
                result = HansardEngine.calculate(engine_data)
                perf.overall_score = result["overall_score"]
                perf.grade = result["grade"]
                perf.structural_score = result["structural_score"]
                perf.debate_score = result["debate_score"]
                perf.save(update_fields=["overall_score", "grade", "structural_score", "debate_score"])

                self.stdout.write(
                    self.style.SUCCESS(f"    -> score: {perf.overall_score}, grade: {perf.grade}")
                )

            updated += 1

        self.stdout.write("")
        self.stdout.write(f"{'Applied' if apply else 'Would update'}: {updated}")
        self.stdout.write(f"Unchanged: {unchanged}")
        self.stdout.write(f"Not found: {not_found}")
        self.stdout.write(f"Skipped (no perf): {skipped}")

        if not apply and updated > 0:
            self.stdout.write(self.style.WARNING("\nRun with --apply to write these changes."))
        elif apply and updated > 0:
            self.stdout.write(self.style.SUCCESS(f"\nDone! {updated} senators updated."))
