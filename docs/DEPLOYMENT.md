# Deployment guide (concurrency-ready)

The app is configured to scale under concurrency when the following are set. All are **optional** for local development (SQLite + in-memory cache work out of the box).

---

## Environment variables

| Variable | Purpose | Example |
|----------|---------|---------|
| **DATABASE_URL** | PostgreSQL connection (when set, SQLite is not used). `conn_max_age=60` is applied. | `postgres://user:pass@localhost:5432/senetrack` |
| **REDIS_URL** | Shared cache and session backend. When set, Redis is used for cache and cache-backed sessions. | `redis://localhost:6379/0` |
| **DJANGO_SECRET_KEY** | Secret key (required in production). | (random 50+ char string) |
| **DJANGO_DEBUG** | Set to `false` or `0` in production. | `false` |
| **ALLOWED_HOSTS** | Comma-separated hosts. | `yourdomain.com,www.yourdomain.com` |
| **GUNICORN_BIND** | Bind address for Gunicorn. | `0.0.0.0:8000` |
| **GUNICORN_WORKERS** | Number of workers (default: CPU*2+1). | `4` |

---

## Running with Gunicorn (production)

1. Install dependencies: `pip install -r requirements.txt`
2. Set env vars (at least `DATABASE_URL` and `REDIS_URL` for production).
3. Run migrations: `python manage.py migrate`
4. Collect static files: `python manage.py collectstatic --noinput`
5. Start Gunicorn:
   ```bash
   gunicorn root.wsgi:application -c gunicorn.conf.py
   ```
   Or without the config file:
   ```bash
   gunicorn root.wsgi:application -w 4 -b 0.0.0.0:8000
   ```

Put **Nginx** (or another reverse proxy) in front to serve static/media and proxy to Gunicorn. WhiteNoise can serve static files from the app if you prefer not to use Nginx for static.

---

## What was adopted for concurrency

- **PostgreSQL**: Use `DATABASE_URL`; `conn_max_age=60` is set automatically.
- **Redis cache**: Set `REDIS_URL`; cache and cache-backed sessions are used.
- **Caching**: Senator rows cached 5 min (`get_senator_rows()`). GeoJSON cached 1 h in Django cache when available. Insights and frontier pages cached 5 min per URL (`@cache_page(300)`).
- **WhiteNoise**: Static files served by WhiteNoise; run `collectstatic` and use `STATICFILES_STORAGE` (CompressedManifest).
- **Gunicorn**: Config in `gunicorn.conf.py`; run with multiple workers.

See `docs/CONCURRENCY_ANALYSIS.md` for the full analysis.
