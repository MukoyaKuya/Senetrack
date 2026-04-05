"""
Apply ALL performance metrics from the authoritative senator_performance_overrides.json to the database.
This implements the 'New (Parliament/Leader Benchmarked)' standard for all senators.

Usage:
    python manage.py sync_performance            # preview changes (dry-run)
    python manage.py sync_performance --apply    # apply changes and recalculate scores
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from scorecard.engine import HansardEngine, perf_to_engine_data
from scorecard.models import ParliamentaryPerformance, Senator

OVERRIDE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "senator_performance_overrides.json"


class Command(BaseCommand):
    help = "Sync senator performance metrics from scorecard/data/senator_performance_overrides.json"

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
        not_found = 0
        skipped = 0
        unchanged = 0

        # Metrics to sync
        metrics = [
            'speeches', 'sponsored_bills', 'passed_bills', 'total_votes', 
            'attended_votes', 'attendance_rate', 'committee_role', 
            'motions_sponsored', 'oversight_actions', 'words_spoken', 
            'sessions_attended', 'county_representation_score'
        ]

        for entry in entries:
            sid = entry["senator_id"]

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

            # Check for any changes (metrics from JSON)
            has_changes = False
            change_details = []
            for m in metrics:
                if m in entry:
                    new_val = entry[m]
                    old_val = getattr(perf, m)
                    if old_val != new_val:
                        has_changes = True
                        change_details.append(f"{m}: {old_val} -> {new_val}")

            if not has_changes:
                unchanged += 1
                continue

            self.stdout.write(f"  {senator.name}: {', '.join(change_details[:3])}{'...' if len(change_details) > 3 else ''}")

            if apply:
                for m in metrics:
                    if m in entry:
                        setattr(perf, m, entry[m])
                
                # RECENT FIX: Standardize on Plenary Attendance (Hansard 2025 standard)
                # 102 is the max plenary sittings for the reported period
                perf.attendance_rate = round((perf.sessions_attended / 102.0) * 100, 1) if perf.sessions_attended else 0
                
                perf.save()

                # Recalculate score via HansardEngine
                engine_data = perf_to_engine_data(perf)
                result = HansardEngine.calculate(engine_data)
                
                perf.overall_score = result["overall_score"]
                perf.grade = result["grade"]
                perf.structural_score = result.get("structural_score", 0)
                perf.debate_score = result.get("debate_score", 0)
                
                perf.save(update_fields=["overall_score", "grade", "structural_score", "debate_score", "attendance_rate"])

                self.stdout.write(
                    self.style.SUCCESS(f"    -> score: {perf.overall_score}, grade: {perf.grade}, attendance: {perf.attendance_rate}%")
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
            self.stdout.write(self.style.SUCCESS(f"\nDone! {updated} senators updated to 'New (Parliament/Leader Benchmarked)' results."))
