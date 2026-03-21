from django.core.management.base import BaseCommand

from scorecard.services.data_fixes import backfill_county_fk


class Command(BaseCommand):
    help = "Populate Senator.county_fk using the legacy string county field."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually write changes to the database. Without this flag, runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        dry_run = not options["apply"]
        result = backfill_county_fk(dry_run=dry_run)

        mode = "DRY RUN" if dry_run else "APPLY"
        self.stdout.write(self.style.WARNING(f"Mode: {mode}"))
        self.stdout.write(f"Updated: {result.updated}")
        self.stdout.write(f"Unmatched: {len(result.unmatched)}")
        self.stdout.write(f"Ambiguous: {len(result.ambiguous)}")

        if result.unmatched:
            self.stdout.write("Unmatched senator_ids:")
            for sid in result.unmatched:
                self.stdout.write(f"  - {sid}")

        if result.ambiguous:
            self.stdout.write("Ambiguous senator_ids:")
            for sid in result.ambiguous:
                self.stdout.write(f"  - {sid}")

