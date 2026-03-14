# Scripts

Utility scripts for the Kenya Senate Scorecard project.

## In this directory

- **`update_senator.py`** — Update a single senator’s `ParliamentaryPerformance` by name or `senator_id`.  
  Run from project root:  
  `python scripts/update_senator.py --name "Cheruiyot" --speeches 2834 --sponsored-bills 18`  
  Or: `python scripts/update_senator.py --id cheruiyot-aaron --attendance 100`

## Management commands (preferred for repeatable tasks)

Use Django management commands from project root:

- `python manage.py import_performance <json_file>`
- `python manage.py import_statements_2025 ...`
- `python manage.py recalculate_hansard_grades`
- `python manage.py backfill_county_fk`
- `python manage.py create_parties_from_senators`
- `python manage.py build_frontier_map_data`
- `python manage.py update_senator ...` (if available in `scorecard/management/commands/`)

See **`docs/DEVELOPER.md`** for full usage.

## Root-level one-off scripts

The project root may contain one-off scripts such as:

- `update_<name>.py` — Senator-specific data fixes (e.g. after manual research).
- `recalc.py`, `mzalendo_importer.py`, `analyze_senators.py`, `check_shakilla.py`, etc.

These are legacy/convenience scripts. For new automation, prefer adding a **management command** under `scorecard/management/commands/` or a script here in `scripts/` with a short note in this README.
