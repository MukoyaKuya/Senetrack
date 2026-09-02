# AWS Free-Tier Deployment Design (IP-only)

**Date:** 2026-07-28  
**Status:** Implemented for AWS prep; **deploy target switched to Oracle Always Free** (see `docs/ORACLE_FREE_TIER.md`)  
**App:** Senetrack (Django scorecard)

## Goal

Deploy Senetrack at no cost, reachable at `http://<public-ip>` only. No custom domain and no HTTPS in this phase. **Primary host: Oracle Cloud Always Free (Ampere A1).** AWS free-tier docs remain as an alternate.

## Success criteria

- App responds on the EC2 public IP over HTTP (port 80).
- Uses existing Neon Postgres and Cloudinary (no RDS/S3/ElastiCache).
- Docker image builds without bundling local `media/`.
- Gunicorn fits a free-tier micro instance (~1 GB RAM).
- Hardcoded Neon credentials removed from the repo; operator rotates the Neon password.
- Operator can follow one doc from zero AWS account → running site.

## Architecture

```
Browser (HTTP)
    → EC2 free-tier micro (Ubuntu)
        → Docker container
            → Gunicorn (1 worker default) + WhiteNoise + Django
                → Neon Postgres (DATABASE_URL)
                → Cloudinary (media)
```

**Explicitly excluded:** Redis/ElastiCache, RDS, S3, ALB, Route 53, Amplify, App Runner, custom domain, TLS/Certbot.

## Account assumptions

- Operator creates a **new** AWS account (no existing account).
- Free plan rules as of mid-2025+: credits / free-tier eligible instances (e.g. `t3.micro`, `t4g.micro`) for a limited period.
- Operator must set a billing alert and stay on eligible instance types/storage.

## Runtime configuration

Required env vars on the instance/container:

| Variable | Value |
|----------|--------|
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | strong random secret |
| `ALLOWED_HOSTS` | EC2 public IP (and later hostname if added) |
| `DATABASE_URL` | Neon connection string |
| `CLOUDINARY_CLOUD_NAME` / `API_KEY` / `API_SECRET` | existing Cloudinary |
| `USE_CLOUDINARY` | `true` (safe even without Cloud Run) |
| `SECURE_SSL_REDIRECT` | `false` (HTTP-only phase) |
| `PORT` | `8080` inside container; host maps `80:8080` |
| `GUNICORN_WORKERS` | `1` (micro RAM) |

Optional: `MAPBOX_ACCESS_TOKEN`, `PLAUSIBLE_DOMAIN`, `DJANGO_ADMIN_PATH`.  
Do **not** set `REDIS_URL` on free tier.

## Repo changes (implementation scope)

1. **`.dockerignore`** — add `media/`, `.venv`, `__pycache__`, sqlite DB, dumps, and other non-runtime junk so builds stay small.
2. **`scripts/start.sh`** — start via `gunicorn.conf.py`; respect `GUNICORN_WORKERS` / `PORT`; keep migrate; make `sync_performance --apply` skippable via env (default: run, or opt-out) so boots are controllable on micro.
3. **`gunicorn.conf.py`** — keep env overrides; ensure defaults are safe when workers set via env (no code change required if start.sh uses `-c` and env).
4. **`.env.example`** — document production vars (no secrets).
5. **`docs/AWS_FREE_TIER.md`** — step-by-step: create AWS account → security group (22, 80) → launch micro EC2 → install Docker → build/run → verify `http://IP`.
6. **`scripts/direct_sql_import.py`** — remove hardcoded Neon URL; require `DATABASE_URL` (or CLI arg) from the environment.

## Operator steps (manual, outside repo)

1. Create AWS account; enable Free plan; set budget alert ($1–$5).
2. Create key pair; security group allowing SSH (22) and HTTP (80) from the operator’s IP (SSH) and `0.0.0.0/0` (HTTP) if public.
3. Launch Ubuntu free-tier eligible instance; note public IP.
4. SSH in; install Docker.
5. Copy project (git clone or `scp`); build image; run container with env file mapping `80:8080`.
6. Open `http://<public-ip>` and confirm home page + static assets.
7. Rotate Neon password after removing the leaked credential from git history / Neon console.

## Security

- Treat the Neon password in `scripts/direct_sql_import.py` as compromised: rotate in Neon console after the script no longer embeds it.
- Never commit `.env` or real `DATABASE_URL`.
- Admin path remains configurable via `DJANGO_ADMIN_PATH`.
- HTTP-only is accepted for this phase; HTTPS is a follow-up when a domain is added.

## Out of scope

- Custom domain, Certbot/ACM, HTTPS redirect on.
- Moving DB/media fully onto AWS.
- CI/CD (GitHub Actions → ECR/EC2).
- Multi-instance / autoscaling.
- Changing product features or templates.

## Follow-up (later)

- Option B/C: domain + HTTPS (Caddy or Nginx + Certbot).
- Optional Elastic Beanstalk if managed deploys are preferred.
- Optional S3 via `django-storages` if leaving Cloudinary.
