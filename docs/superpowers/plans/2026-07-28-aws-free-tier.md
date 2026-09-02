# AWS Free-Tier (IP-only) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare Senetrack for free-tier EC2 HTTP-by-IP deploy using Docker, Neon, and Cloudinary.

**Architecture:** Keep the existing Docker + Gunicorn + WhiteNoise stack; harden ignore/start scripts for micro instances; document AWS account → EC2 → Docker run; remove leaked Neon credentials from the import script.

**Tech Stack:** Django, Gunicorn, Docker, Neon Postgres, Cloudinary, AWS EC2 free-tier micro.

## Global Constraints

- Public URL is HTTP IP only (`SECURE_SSL_REDIRECT=false`); no domain/HTTPS this phase.
- No Redis, RDS, S3, ALB, or Route 53.
- Do not commit secrets or real `.env` values.
- Do not commit unless the user explicitly asks.
- Preserve Cloud Run compatibility (`PORT`, existing Docker CMD).

## File map

| File | Responsibility |
|------|----------------|
| `.dockerignore` | Keep build context small (exclude `media/`, venvs, dumps) |
| `scripts/start.sh` | Migrate, optional sync, Gunicorn via config + env |
| `scripts/direct_sql_import.py` | Import voting records using env/CLI DB URL only |
| `.env.example` | Document required production env vars |
| `docs/AWS_FREE_TIER.md` | Zero-to-running EC2 guide for new AWS accounts |

---

### Task 1: Harden Docker build context

**Files:**
- Modify: `.dockerignore`

**Interfaces:**
- Produces: Docker builds that exclude `media/` and local junk

- [ ] **Step 1: Replace `.dockerignore` contents**

```
.venv/
venv/
ENV/
env/
__pycache__/
*.py[cod]
*$py.class
*.sqlite3
db.sqlite3
.env
.env.*
!.env.example
.git/
.gitignore
.gcloudignore
.agents/
.agent/
.gemini/
.vscode/
.idea/
media/
staticfiles/
static_root/
docs/
*.md
!requirements.txt
*.dump
*_dump.json
voting_records_dump.json
```

- [ ] **Step 2: Verify `media/` is listed**

Run: `Select-String -Path .dockerignore -Pattern '^media/'`
Expected: a match for `media/`

---

### Task 2: Micro-friendly startup script

**Files:**
- Modify: `scripts/start.sh`

**Interfaces:**
- Consumes: `PORT`, `GUNICORN_BIND`, `GUNICORN_WORKERS`, `SKIP_SYNC_PERFORMANCE`
- Produces: container process bound to `0.0.0.0:$PORT` via `gunicorn.conf.py`

- [ ] **Step 1: Rewrite `scripts/start.sh`**

```bash
#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

if [ "${SKIP_SYNC_PERFORMANCE:-false}" != "true" ]; then
  echo "Syncing performance data from JSON..."
  python manage.py sync_performance --apply
else
  echo "Skipping sync_performance (SKIP_SYNC_PERFORMANCE=true)"
fi

export GUNICORN_BIND="${GUNICORN_BIND:-0.0.0.0:${PORT:-8080}}"
export GUNICORN_WORKERS="${GUNICORN_WORKERS:-2}"

echo "Starting Gunicorn on ${GUNICORN_BIND} with ${GUNICORN_WORKERS} worker(s)..."
exec gunicorn root.wsgi:application -c gunicorn.conf.py
```

- [ ] **Step 2: Confirm script is executable intent in Dockerfile** (`chmod +x` already present)

---

### Task 3: Remove hardcoded Neon credentials

**Files:**
- Modify: `scripts/direct_sql_import.py`

**Interfaces:**
- Consumes: `DATABASE_URL` env or CLI arg `sys.argv[2]`
- Produces: same `direct_import(json_file, db_url)` behavior without embedded secrets

- [ ] **Step 1: Change `__main__` to require env/CLI URL**

```python
if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "voting_records_dump.json"
    db_url = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        print("Usage: python scripts/direct_sql_import.py [json_file] [database_url]", file=sys.stderr)
        print("Or set DATABASE_URL.", file=sys.stderr)
        sys.exit(1)
    direct_import(json_file, db_url)
```

Add `import os` at top.

- [ ] **Step 2: Grep repo for embedded Neon credentials**

Run: `rg "postgresql://neondb_owner:" -n`
Expected: no matches in runtime scripts

---

### Task 4: Env template + AWS free-tier guide

**Files:**
- Create: `.env.example`
- Create: `docs/AWS_FREE_TIER.md`

**Interfaces:**
- Produces: operator can create AWS account and run Docker with documented env

- [ ] **Step 1: Create `.env.example`** with placeholders for all required vars from the spec (no real secrets).

- [ ] **Step 2: Create `docs/AWS_FREE_TIER.md`** covering:
  1. Create AWS account + budget alert
  2. Key pair + security group (22 from your IP, 80 from anywhere)
  3. Launch Ubuntu free-tier micro
  4. Install Docker
  5. Clone/build/run with `--env-file` and `-p 80:8080`
  6. Set `ALLOWED_HOSTS=<public-ip>` and `SECURE_SSL_REDIRECT=false`
  7. Verify `http://<public-ip>`
  8. Rotate Neon password (credential was previously in repo)

- [ ] **Step 3: Spot-check docs mention `GUNICORN_WORKERS=1` and no Redis**

---

### Task 5: Local verification

**Files:** none (verify only)

- [ ] **Step 1: Confirm start.sh and .dockerignore on disk**
- [ ] **Step 2: Confirm no hardcoded Neon password remains**
- [ ] **Step 3: Summarize manual AWS steps for the operator**

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| `.dockerignore` media exclusion | Task 1 |
| `start.sh` + workers + skip sync | Task 2 |
| Remove Neon secret | Task 3 |
| `.env.example` | Task 4 |
| `docs/AWS_FREE_TIER.md` | Task 4 |
| Operator manual steps | Task 4–5 |
| No Redis/RDS/S3 | Task 4 docs |
| `SECURE_SSL_REDIRECT=false` | Task 4 |
