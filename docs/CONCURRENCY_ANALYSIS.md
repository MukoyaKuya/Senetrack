# Concurrency Analysis — ReportFormv2 (SENETRACK)

This document summarizes whether the platform can handle **high concurrency** and what to change to improve it.

**Status:** The recommendations below have been **adopted** in code. See `docs/DEPLOYMENT.md` for how to enable them (PostgreSQL, Redis, Gunicorn) and run in production.

---

## Executive summary

**Current state:** The app is **not** well suited for high concurrency. It will handle low-to-moderate traffic (e.g. tens of concurrent users) but will become a bottleneck under sustained high load. The main limits are: **SQLite**, **no shared caching** for heavy views, and **CPU-heavy work per request** on insights/frontier.

**To handle big concurrency** you need: a proper RDBMS (PostgreSQL), a shared cache (e.g. Redis), caching of expensive views, and production deployment (multiple workers, static/media offload).

---

## 1. Database

| Aspect | Current | Impact on concurrency |
|--------|---------|------------------------|
| **Engine** | `django.db.backends.sqlite3` | **Critical.** SQLite uses a single writer and file-level locking. Many concurrent requests cause lock contention and serialized writes. |
| **CONN_MAX_AGE** | Not set (default 0) | Each request gets a new connection; with SQLite this is less harmful than with PostgreSQL but still no connection reuse. |

**Recommendation:** For production and any real concurrency, use **PostgreSQL** (or MySQL/MariaDB). Then set `CONN_MAX_AGE` (e.g. 60–300) and use a connection pooler (e.g. PgBouncer) if you run many workers.

---

## 2. Heavy per-request work (CPU + DB)

| Location | What runs | Concurrency impact |
|----------|-----------|---------------------|
| **`/insights/`** (`data_insights`) | `build_senator_rows()` then many `sorted()` / list comprehensions / aggregations in Python | One full senator scan + engine work per request; no cache. Under load, every insight request pays full cost. |
| **`/frontier/`** (`frontier_insights`) | Same `build_senator_rows()` | Same as above. |
| **`build_senator_rows()`** | Single ORM query with `select_related("perf", "county_fk")`, then a Python loop calling `get_engine_result(perf)` for each senator | Good: one query (no N+1). Bad: CPU cost scales with senator count and is paid on every insights/frontier request. |

So the **insights and frontier pages** are the main CPU and logical “DB” hotspots. They are not cached.

**Recommendation:** Cache the result of `build_senator_rows()` or the entire response of `/insights/` and `/frontier/` (e.g. with a shared cache and short TTL, e.g. 5–15 minutes). Optionally precompute aggregates in a background job and serve from cache.

---

## 3. Caching

| Aspect | Current | Impact |
|--------|---------|--------|
| **Django CACHES** | Not set in `settings.py` | Default is **LocMemCache** (in-process). With multiple workers/processes, each has its own cache; no shared cache. |
| **Page/view cache** | Only senator detail uses `@cache_page(60 * 2)` (2 min) | Insights and frontier are uncached. |
| **GeoJSON** | In-process dict `_geojson_cache` with TTL 1h in `insights.py` | Per-process; on cache miss, `urllib.request.urlopen()` blocks. Multiple workers can each hit the URL. |

**Recommendation:** Configure a **shared cache backend** (e.g. Redis or Memcached). Use it for:

- `cache_page` or template fragment / view-level cache for `/insights/` and `/frontier/`.
- Optional: cache `build_senator_rows()` output (or a hash of it) with a short TTL.
- Session backend: `django.contrib.sessions.backends.cache` (or Redis) so session reads/writes don’t hit the DB on every request.

---

## 4. Sessions

| Aspect | Current | Impact |
|--------|---------|--------|
| **SESSION_ENGINE** | Not set → default **database** | Every request that touches the session does a DB read (and possibly write). Under concurrency this adds load and lock contention on SQLite. |

**Recommendation:** With a shared cache (e.g. Redis), use cache-backed sessions to reduce DB load and improve concurrency.

---

## 5. Blocking I/O and external calls

| Location | Behavior | Impact |
|----------|----------|--------|
| **`_fetch_kenya_geojson()`** | On cache miss: `urllib.request.urlopen(..., timeout=10)` or read from local file | Blocking; holds a worker/thread for up to 10s. With in-process cache, first request per worker pays this. |

**Recommendation:** Keep the in-memory cache but consider prewarming (e.g. at startup or via a management command). With a shared cache, store GeoJSON (or frontier map data) there so only one worker ever fetches it.

---

## 6. Application server and workers

| Aspect | Current | Impact |
|--------|---------|--------|
| **WSGI** | `root.wsgi.application` (synchronous) | All views are synchronous; one request per worker at a time. |
| **ASGI** | `asgi.py` present but not used in settings for runserver | No async views; no direct concurrency gain from ASGI in current code. |
| **Runserver** | Single process, single thread (typical local use) | Not for production; only one request at a time. |

**Recommendation:** Run under **Gunicorn** (or uWSGI) with **multiple workers** (e.g. 2–4 × CPU cores). Put **Nginx** (or another reverse proxy) in front for static/media and proxy to the app. This gives real process-level concurrency.

---

## 7. Static and media files

| Aspect | Current | Impact |
|--------|---------|--------|
| **STATIC_URL / MEDIA_URL** | Served by Django when using `runserver` | In production, serving files from Django wastes worker capacity and hurts concurrency. |

**Recommendation:** Use **WhiteNoise** for static files and serve **media** from a separate store (e.g. S3) or a dedicated path via Nginx/CDN so Django workers only handle app logic.

---

## 8. What is already in good shape

- **ORM usage:** `select_related("perf", "county_fk")` and `prefetch_related` where used (e.g. county view) avoid N+1 queries.
- **Senator detail:** Cached for 2 minutes with `@cache_page(60 * 2)`.
- **GeoJSON:** Cached in-process with TTL to avoid repeated URL fetch per request (within the same process).

---

## 9. Recommended changes (in order of impact)

1. **Switch to PostgreSQL** and set `CONN_MAX_AGE` for production.
2. **Add a shared cache (Redis)** and set `CACHES` and optionally `SESSION_ENGINE` to use it.
3. **Cache insights and frontier** (e.g. `@cache_page(300)` or cache `build_senator_rows()` + filter result) so repeated traffic doesn’t recompute everything.
4. **Use cache-backed sessions** to reduce DB load under concurrency.
5. **Run with Gunicorn + multiple workers** behind Nginx (or similar).
6. **Serve static/media** via WhiteNoise and/or CDN/reverse proxy so Django workers are not serving files.

After these, the platform can handle **much higher concurrency** (hundreds of concurrent users, depending on hardware and cache hit rates). Without them, expect **tens of concurrent users** to be the practical limit, with SQLite and uncached heavy views as the main bottlenecks.
