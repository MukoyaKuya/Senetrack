"""
Sync all app data from the remote cloud database (Neon.tech / PostgreSQL) into the
local SQLite database so that you can work fully offline.

Usage:
    python manage.py sync_from_remote

The command reads DATABASE_URL from the environment. It temporarily registers
the remote DB as a second Django database alias, dumps every scorecard model,
then loads the dump into the local default (SQLite) database.

You can also pass a URL directly:
    python manage.py sync_from_remote --database-url "postgresql://..."
"""
import os
from pathlib import Path

import dj_database_url
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

# Tables that are auto-created by Django and must not be synced
# (they differ by environment and cause conflicts on loaddata).
EXCLUDE_APPS = [
    "contenttypes",
    "auth.permission",
    "admin.logentry",
    "sessions.session",
]

# Only sync these apps — everything owned by this project.
SYNC_APPS = [
    "scorecard",
]


class Command(BaseCommand):
    help = "Sync all data from the remote cloud database into local SQLite for offline development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database-url",
            dest="database_url",
            default="",
            help="Remote DATABASE_URL to pull from (defaults to DATABASE_URL env var).",
        )
        parser.add_argument(
            "--no-migrate",
            action="store_true",
            default=False,
            help="Skip running migrations on the local database before loading.",
        )

    def handle(self, *args, **options):
        database_url = (options["database_url"] or os.environ.get("DATABASE_URL", "")).strip()
        if not database_url:
            raise CommandError(
                "No remote database URL found.\n"
                "Set DATABASE_URL in your environment or pass --database-url <url>."
            )

        # ── 1. Register the remote DB temporarily ────────────────────────────
        self.stdout.write("Connecting to remote database…")
        try:
            remote_cfg = dj_database_url.parse(database_url, conn_max_age=0)
        except Exception as exc:
            raise CommandError(f"Could not parse DATABASE_URL: {exc}") from exc

        settings.DATABASES["_remote_sync"] = remote_cfg

        dump_path = Path(settings.BASE_DIR) / "sync_dump.json"

        try:
            # ── 2. Quick connectivity check ───────────────────────────────────
            self._check_remote_connection()

            # ── 3. Ensure local schema is current ─────────────────────────────
            if not options["no_migrate"]:
                self.stdout.write("Applying local migrations…")
                call_command("migrate", "--run-syncdb", verbosity=0)

            # ── 4. Dump from remote ───────────────────────────────────────────
            self.stdout.write("Dumping data from remote database (this may take a moment)…")
            exclude_flags = []
            for app in EXCLUDE_APPS:
                exclude_flags += ["--exclude", app]

            call_command(
                "dumpdata",
                *SYNC_APPS,
                "--database=_remote_sync",
                f"--output={dump_path}",
                "--indent=2",
                *exclude_flags,
                verbosity=0,
            )

            row_count = self._count_rows(dump_path)
            self.stdout.write(f"  → {row_count} objects exported.")

            # ── 5. Wipe existing local data for the synced apps ───────────────
            self.stdout.write("Clearing existing local data…")
            self._flush_apps(SYNC_APPS)

            # ── 6. Load into local SQLite ─────────────────────────────────────
            self.stdout.write("Loading data into local SQLite database…")
            call_command("loaddata", str(dump_path), "--database=default", verbosity=1)

            self.stdout.write(
                self.style.SUCCESS(
                    "\n✓ Sync complete! "
                    "Your local SQLite database now mirrors the cloud database.\n"
                    "  Start the server normally: python manage.py runserver"
                )
            )

        except Exception as exc:
            # Friendly message for the most common failure (no internet)
            msg = str(exc)
            if "could not translate host name" in msg or "Name or service not known" in msg:
                raise CommandError(
                    "Could not reach the remote database — are you offline?\n"
                    f"Detail: {msg}"
                ) from exc
            raise

        finally:
            # Always clean up the temp dump file and the extra DB alias
            if dump_path.exists():
                dump_path.unlink()
            settings.DATABASES.pop("_remote_sync", None)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _check_remote_connection(self):
        """Attempt a trivial query against the remote DB to fail fast if offline."""
        from django.db import connections
        try:
            conn = connections["_remote_sync"]
            conn.ensure_connection()
        except Exception as exc:
            raise CommandError(
                f"Cannot connect to remote database: {exc}\n"
                "Check your internet connection and DATABASE_URL."
            ) from exc

    def _count_rows(self, path: Path) -> int:
        """Return the number of serialized objects in a JSON dump file."""
        import json
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return len(data)
        except Exception:
            return 0

    def _flush_apps(self, app_labels: list):
        """Delete all rows for the given app labels from the local DB."""
        from django.apps import apps as django_apps
        from django.db import connection

        with connection.schema_editor() as schema_editor:
            pass  # just ensure schema is available

        for app_label in app_labels:
            app_config = django_apps.get_app_config(app_label)
            # Reverse model dependency order to avoid FK constraint errors
            models = list(reversed(list(app_config.get_models())))
            for model in models:
                try:
                    model.objects.using("default").all().delete()
                except Exception as exc:
                    self.stderr.write(f"  Warning: could not clear {model.__name__}: {exc}")
