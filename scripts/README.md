# Scripts

Utility scripts for the Kenya Senate Scorecard project.

## Preferred: management commands (scalable ETL)

Use these from project root instead of one-off scripts:

- **`python manage.py apply_senator_updates`** — **Unified senator/perf updates** (config-driven or CLI).  
  - Bulk: `--config updates.json` (see `docs/updates_example.json`).  
  - Single: `--id <senator_id>` or `--name "Partial"` plus `--speeches`, `--party`, `--words-spoken`, etc.  
  Replaces the need for many `update_<name>.py` scripts.
- `python manage.py import_performance <json_file>`
- `python manage.py import_statements_2025 ...`
- `python manage.py recalculate_hansard_grades`
- `python manage.py backfill_county_fk`
- `python manage.py create_parties_from_senators`
- `python manage.py build_frontier_map_data`
- `python manage.py update_senator <id> --party "X"` — Senator profile-only updates (name, party, image_url, county, etc.).

See **`docs/DEVELOPER.md`** for full usage.

## In this directory

- **`update_senator.py`** — Standalone script to update one senator’s **performance** by `--id` or `--name`.  
  Prefer **`manage.py apply_senator_updates --id X --speeches 100`** for consistency and to avoid maintaining duplicate logic.

## Root-level one-off scripts (legacy)

The project root may contain:

- `update_<name>.py` — One-off senator fixes. Prefer **`apply_senator_updates --config <file>`** or CLI for new updates.
- `recalc.py`, `mzalendo_importer.py`, `analyze_senators.py`, etc.

For new automation, use **management commands** or add a script here and document it in this README.
