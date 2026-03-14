"""
Configuration-driven and CLI senator/perf updates. Replaces one-off update_<name>.py scripts.

Bulk (config file):
  python manage.py apply_senator_updates --config updates.json
  python manage.py apply_senator_updates --config updates.json --dry-run

Single senator (CLI):
  python manage.py apply_senator_updates --id cheruiyot-aaron --speeches 100 --party "UDA"
  python manage.py apply_senator_updates --name "Cheruiyot" --perf-speeches 500 --perf-words-spoken 120000

Config JSON shape (array of updates):
  [
    {
      "senator_id": "cheruiyot-aaron",
      "senator": { "party": "UDA", "image_url": "https://..." },
      "perf": { "speeches": 945, "words_spoken": 116604, "sponsored_bills": 18 }
    },
    { "name": "Sifuna", "perf": { "overall_score": 89, "grade": "A" } }
  ]
  Match by senator_id (exact) or name (partial, first match). Omit senator or perf if no updates.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scorecard.models import County, ParliamentaryPerformance, Senator

# Allowed keys for Senator (and CLI: pass as --party, --image-url, etc.)
SENATOR_KEYS = {
    "name",
    "party",
    "image_url",
    "nomination",
    "is_deceased",
    "is_still_computing",
    "county_slug",
}
# Allowed keys for ParliamentaryPerformance
PERF_KEYS = {
    "speeches",
    "attendance_rate",
    "sponsored_bills",
    "passed_bills",
    "amendments",
    "committee_role",
    "committee_attendance",
    "total_votes",
    "attended_votes",
    "oversight_actions",
    "county_representation_score",
    "words_spoken",
    "motions_sponsored",
    "sessions_attended",
    "statements_2025",
    "statements_total",
    "overall_score",
    "grade",
    "structural_score",
    "debate_score",
}


def resolve_senator(senator_id=None, name=None):
    if senator_id:
        return Senator.objects.filter(senator_id=senator_id).first()
    if name:
        s = Senator.objects.filter(name__icontains=name.strip()).first()
        if s:
            return s
        parts = name.strip().split()
        if len(parts) > 1:
            return Senator.objects.filter(name__icontains=parts[-1]).first()
    return None


def apply_senator_updates(senator, senator_data, dry_run=False):
    if not senator_data:
        return 0
    updates = []
    for key, value in senator_data.items():
        if key not in SENATOR_KEYS:
            continue
        if key == "county_slug":
            county = County.objects.filter(slug=value).first()
            if county:
                senator.county_fk = county
                updates.append("county_fk")
            continue
        if key == "is_deceased":
            senator.is_deceased = bool(value)
            updates.append(key)
            continue
        if key == "is_still_computing":
            senator.is_still_computing = bool(value)
            updates.append(key)
            continue
        if getattr(senator, key, None) != value:
            setattr(senator, key, value)
            updates.append(key)
    if updates and not dry_run:
        senator.save()
    return len(updates)


def apply_perf_updates(senator, perf_data, dry_run=False):
    if not perf_data:
        return 0
    try:
        perf = senator.perf
    except ParliamentaryPerformance.DoesNotExist:
        perf = ParliamentaryPerformance(senator=senator) if not dry_run else None
        if not perf:
            return 0
    updates = []
    for key, value in perf_data.items():
        if key not in PERF_KEYS:
            continue
        if getattr(perf, key, None) != value:
            setattr(perf, key, value)
            updates.append(key)
    if updates and not dry_run:
        perf.save()
    return len(updates)


class Command(BaseCommand):
    help = "Apply senator and/or performance updates from a JSON config file or CLI (single senator)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--config",
            type=str,
            help="Path to JSON file: array of { senator_id|name, senator?: {}, perf?: {} }",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Log what would be updated without saving.",
        )
        # Single-senator mode
        parser.add_argument("--id", dest="senator_id", help="Senator ID (exact).")
        parser.add_argument("--name", help="Senator name (partial match).")
        # Senator fields (CLI)
        parser.add_argument("--party")
        parser.add_argument("--image-url", dest="image_url")
        parser.add_argument("--nomination")
        parser.add_argument("--county-slug", dest="county_slug")
        parser.add_argument("--is-deceased", action="store_true", dest="is_deceased")
        parser.add_argument("--is-still-computing", action="store_true", dest="is_still_computing")
        # Perf fields (CLI): prefix with --perf- or allow known names
        for key in sorted(PERF_KEYS):
            parser.add_argument(f"--{key.replace('_', '-')}", dest=f"perf_{key}", type=self._type_for(key))

    @staticmethod
    def _type_for(key):
        if key in ("overall_score", "structural_score", "debate_score", "attendance_rate",
                   "committee_attendance", "county_representation_score"):
            return float
        if key in ("grade", "committee_role"):
            return str
        return int

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        config_path = options.get("config")

        if config_path:
            self._run_config(config_path, dry_run)
            return

        # Single-senator CLI mode
        senator_id = options.get("senator_id")
        name = options.get("name")
        if not senator_id and not name:
            raise CommandError("Provide --config <file>, or --id / --name for a single senator.")

        senator = resolve_senator(senator_id=senator_id, name=name)
        if not senator:
            raise CommandError(f"Senator not found (id={senator_id!r}, name={name!r}).")

        senator_data = {}
        for k in ("party", "image_url", "nomination", "county_slug"):
            v = options.get(k)
            if v is not None:
                senator_data[k] = v
        if options.get("is_deceased"):
            senator_data["is_deceased"] = True
        if options.get("is_still_computing"):
            senator_data["is_still_computing"] = True

        perf_data = {}
        for k in PERF_KEYS:
            v = options.get(f"perf_{k}")
            if v is not None:
                perf_data[k] = v

        if not senator_data and not perf_data:
            raise CommandError("No senator or perf fields given. Use --party, --speeches, etc.")

        sc = apply_senator_updates(senator, senator_data, dry_run=dry_run)
        pc = apply_perf_updates(senator, perf_data, dry_run=dry_run)
        msg = f"Updated {senator.name} ({senator.senator_id}): senator={sc}, perf={pc}"
        if dry_run:
            msg = "[DRY RUN] " + msg
        self.stdout.write(self.style.SUCCESS(msg))

    def _run_config(self, config_path, dry_run):
        path = Path(config_path)
        if not path.exists():
            raise CommandError(f"Config file not found: {config_path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise CommandError("Config JSON must be an array of update objects.")

        updated = 0
        not_found = 0
        for i, item in enumerate(data):
            senator_id = item.get("senator_id")
            name = item.get("name")
            senator = resolve_senator(senator_id=senator_id, name=name)
            if not senator:
                not_found += 1
                self.stderr.write(self.style.WARNING(f"Row {i + 1}: senator not found (id={senator_id!r}, name={name!r})."))
                continue
            senator_data = {k: v for k, v in (item.get("senator") or {}).items() if k in SENATOR_KEYS}
            perf_data = {k: v for k, v in (item.get("perf") or {}).items() if k in PERF_KEYS}
            sc = apply_senator_updates(senator, senator_data, dry_run=dry_run)
            pc = apply_perf_updates(senator, perf_data, dry_run=dry_run)
            if sc or pc:
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"  {senator.senator_id}: senator={sc}, perf={pc}"))

        self.stdout.write(self.style.SUCCESS(f"Done: {updated} updated, {not_found} not found." + (" (dry run)" if dry_run else "")))
