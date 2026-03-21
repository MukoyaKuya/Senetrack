from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from scorecard.data.voting_records import VOTING_DATA
from scorecard.models import Senator, VotingRecord
from scorecard.management.commands.apply_senator_updates import resolve_senator


TITLE_TO_SOURCE = {
    "The County Governments Allocation Bill, 2025 (Committee of the Whole)": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/15/",
    "Sugar Bill": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/13/",
    "Rigathi Gachagua Impeachment - Grounds 11": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/12/",
    "Rigathi Gachagua Impeachment - Grounds 6": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/7/",
    "Rigathi Gachagua Impeachment - Grounds 7": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/8/",
    "Rigathi Gachagua Impeachment - Grounds 8": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/9/",
    "Rigathi Gachagua Impeachment - Grounds 9": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/10/",
    "Rigathi Gachagua Impeachment - Grounds 10": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/11/",
    "Rigathi Gachagua Impeachment - Grounds 5": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/6/",
    "Business Laws (Amendment) Bill 2024": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/14/",
    "Rigathi Gachagua Impeachment - Grounds 3": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/4/",
    "Rigathi Gachagua Impeachment - Grounds 4": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/5/",
    "Rigathi Gachagua Impeachment - Grounds 1": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/2/",
    "Rigathi Gachagua Impeachment - Grounds 2": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/3/",
    "Kisii Deputy Governor Impeachment - Grounds 3": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/18/",
    "Kisii Deputy Governor Impeachment - Grounds 1": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/16/",
    "Kisii Deputy Governor Impeachment - Grounds 2": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/17/",
    "Kisii Deputy Governor Impeachment - Grounds 4": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/19/",
    "Affordable Housing Bill 2024": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/1/",
    "The Social Health Insurance Bill (National Assembly Bill No. 58 of 2023)": "https://mzalendo.com/research-and-knowledge/voting-patterns/senate/20/",
}


def _parse_title_and_date(raw: str):
    """
    Split the combined label into (title, date).
    Example: "Sugar Bill - Oct 29, 2024" -> ("Sugar Bill", date(2024,10,29)).
    """
    base, datestr = raw.rsplit(" - ", 1)
    date_val = datetime.strptime(datestr.strip(), "%b %d, %Y").date()
    return base, date_val


def _normalize_decision(decision: str) -> str:
    d = (decision or "").strip()
    if not d:
        return "Absent"
    lower = d.lower()
    if lower in {"abstained", "abstain"}:
        return "Abstain"
    if lower in {"yes", "no", "absent"}:
        return lower.capitalize()
    return d


class Command(BaseCommand):
    help = "Import structured voting records into VotingRecord from VOTING_DATA"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and resolve senators but do not write to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created = 0
        updated = 0
        missing_senators = []

        with transaction.atomic():
            for name, votes in VOTING_DATA.items():
                senator = resolve_senator(name=name)
                if not senator:
                    missing_senators.append(name)
                    continue

                for raw_title, decision in votes.items():
                    base_title, date_val = _parse_title_and_date(raw_title)
                    norm_decision = _normalize_decision(decision)
                    source = TITLE_TO_SOURCE.get(base_title, "")

                    if dry_run:
                        continue

                    obj, was_created = VotingRecord.objects.update_or_create(
                        senator=senator,
                        date=date_val,
                        title=base_title,
                        defaults={
                            "decision": norm_decision,
                            "source": source,
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

            if dry_run:
                transaction.set_rollback(True)

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete – no records written."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Voting records import complete. Created {created}, updated {updated}."
                )
            )

        if missing_senators:
            unique_missing = sorted(set(missing_senators))
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {len(unique_missing)} senator name(s) with no match in DB: "
                    + ", ".join(unique_missing)
                )
            )

