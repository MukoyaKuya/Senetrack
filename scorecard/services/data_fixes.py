from dataclasses import dataclass
from typing import List, Optional

from django.db import transaction

from scorecard.models import Senator, County


@dataclass
class BackfillResult:
    updated: int
    unmatched: List[str]
    ambiguous: List[str]


def _match_county(counties: List[County], county_name: str) -> Optional[County]:
    """
    Best-effort match of a raw senator.county string to a County.

    This mirrors the logic used in the 0011_add_senator_county_fk migration
    so that it can be safely re-run from a management command.
    """
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


def backfill_county_fk(dry_run: bool = True) -> BackfillResult:
    """
    Populate Senator.county_fk using the legacy string county field.

    When dry_run=True, no changes are committed, but stats are still returned.
    """
    senators = Senator.objects.filter(county_fk__isnull=True)
    counties = list(County.objects.all())

    updated = 0
    unmatched: List[str] = []
    ambiguous: List[str] = []  # Reserved for future, if we add multi-match detection

    if not counties or not senators.exists():
        return BackfillResult(updated=0, unmatched=[], ambiguous=[])

    with transaction.atomic():
        for senator in senators:
            raw_county = getattr(senator, "county", "") or ""
            match = _match_county(counties, raw_county)
            if match:
                senator.county_fk_id = match.id
                updated += 1
                if not dry_run:
                    senator.save(update_fields=["county_fk"])
            else:
                unmatched.append(senator.senator_id)

        if dry_run:
            transaction.set_rollback(True)

    return BackfillResult(updated=updated, unmatched=unmatched, ambiguous=ambiguous)

