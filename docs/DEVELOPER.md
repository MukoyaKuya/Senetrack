# Developer Guide — Kenya Senate Scorecard

Quick reference for running, testing, and updating the ReportFormv2 codebase.

## Setup

- **Python:** 3.10+
- **Database:** SQLite by default; set `DATABASE_URL` for PostgreSQL in production.
- **Optional:** `REDIS_URL` for cache/sessions; `MAPBOX_ACCESS_TOKEN` for frontier map.

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8001
```

App: <http://127.0.0.1:8001/>  
Admin: <http://127.0.0.1:8001/admin/>

---

## Running Tests

```bash
python manage.py test scorecard.tests
```

Tests cover: SenatorPerformanceEngine, HansardEngine, `get_engine_result`, `perf_to_engine_data`, analytics (`normalize_frontier`, `build_senator_rows`), county/frontier normalization, insights chart-building, and main views (home, senator list/detail, compare, county list/detail, data-insights, frontier-insights).

---

## Data Import & Recalculation

### Import performance data (JSON)

Bulk-update senator performance from an exported JSON file:

```bash
python manage.py import_performance path/to/senator_performance_data.json
```

### Import Statements Tracker (2025)

Import statement counts from the official tracker (e.g. CSV or JSON):

```bash
python manage.py import_statements_2025  # see command help for args
```

### Recalculate Hansard grades

Recompute overall score, grade, structural/debate scores from the Hansard 2025 engine and update `ParliamentaryPerformance`:

```bash
python manage.py recalculate_hansard_grades
```

Uses embedded report data; run after importing new Hansard metrics or when the engine formula changes.

### Backfill county FK

Link senators to the County model by name/slug:

```bash
python manage.py backfill_county_fk
```

### Create parties from senators

Create `Party` records from distinct senator party names:

```bash
python manage.py create_parties_from_senators
```

---

## Frontier Map (static GeoJSON)

Pre-build the frontier map JSON so the map loads without calling Django:

```bash
python manage.py build_frontier_map_data
```

Output: `scorecard/static/scorecard/kenya_counties.geojson` (or path shown in command output). Run after changing counties or regions.

---

## Caching

- **Senator rows** (insights/frontier): 5-minute TTL, key `scorecard:senator_rows`. Clear with Django cache backend (e.g. `cache.delete("scorecard:senator_rows")` or restart with locmem).
- **Insights / frontier views:** Page cache 5 min (`@cache_page(300)`). Restart runserver or wait for expiry to see data changes.

---

## Environment Variables

| Variable | Purpose |
|--------|---------|
| `DATABASE_URL` | PostgreSQL connection (optional; default SQLite) |
| `REDIS_URL` | Redis for cache and sessions (optional) |
| `DJANGO_SECRET_KEY` | Secret key (required in production) |
| `DJANGO_DEBUG` | `true` / `false` (default `true`) |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `MAPBOX_ACCESS_TOKEN` | Mapbox token for frontier map |
| `KENYA_COUNTIES_GEOJSON_URL` | Optional GeoJSON URL for counties |
| `ACTIVE_DEBATES` | Integer; app config (default 12) |

---

## Project Layout

- **`scorecard/`** — Main Django app: models, views, engine, services, templates, static.
- **`scorecard/engine.py`** — Scoring: `HansardEngine`, `SenatorPerformanceEngine`, `get_engine_result`, `perf_to_engine_data`.
- **`scorecard/services/`** — `analytics` (senator rows, cache), `senators` (frontier, display), `county_frontier` (region/slug maps), `insights_charts` (chart data for insights).
- **`scorecard/management/commands/`** — Management commands (import, recalc, backfill, build_frontier_map_data, etc.).
- **`root/`** — Project settings, URLs, WSGI/ASGI.
- **`docs/`** — Documentation (this file).
- **`scripts/`** — Utility scripts; see `scripts/README.md`. One-off senator updates (e.g. `update_*.py`) may live in project root; prefer management commands or `scripts/` for new automation.

---

## Code Conventions

- Use `get_engine_result(perf)` for any senator score/grade display; it picks Hansard vs legacy engine.
- Frontier/filter normalization: `normalize_frontier()` in `scorecard.services.analytics`.
- County name/region/slug for maps: `scorecard.services.county_frontier` (`build_county_maps`, `resolve_region`).
- Insights chart data: built by `scorecard.services.insights_charts.build_insights_charts(aggregates)`.
