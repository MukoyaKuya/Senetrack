# Deploying Senetrack on Render

This guide outlines deploying Senetrack to [Render](https://render.com) using containerized Docker execution with Python 3.14.

---

## 1. Prerequisites
- A [Render](https://render.com) account.
- Your project pushed to GitHub.
- (Optional) Cloudinary account for media assets (avatars, logos).

---

## 2. Deployment Methods

### Method 1: Infrastructure as Code with `render.yaml` (Blueprint)
The repository includes a [`render.yaml`](file:///c:/Users/Little%20Human/Desktop/Django/Senetrack/render.yaml) blueprint specification:
1. In Render Dashboard, click **New +** > **Blueprint**.
2. Select your repository.
3. Review the blueprint and enter any missing secret keys.
4. Click **Apply**.

### Method 2: Manual Web Service Setup
1. In Render Dashboard, click **New +** > **Web Service**.
2. Connect your GitHub repository.
3. Select **Docker** as the runtime (Render will automatically pick up `Dockerfile`).
4. Choose your preferred region and tier (Free or Starter).
5. Add the Environment Variables below.
6. Click **Create Web Service**.

---

## 3. Environment Variables Reference

| Variable | Required | Example / Description |
| :--- | :--- | :--- |
| `DJANGO_DEBUG` | **Yes** | `false` |
| `DJANGO_SECRET_KEY` | **Yes** | 50+ character secure random string |
| `SECURE_SSL_REDIRECT` | **Yes** | `true` |
| `USE_CLOUDINARY` | Optional | `true` |
| `CLOUDINARY_CLOUD_NAME`| Optional | Your Cloudinary cloud name |
| `CLOUDINARY_API_KEY`   | Optional | Your Cloudinary API key |
| `CLOUDINARY_API_SECRET`| Optional | Your Cloudinary API secret |
| `DATABASE_URL`         | Optional | `postgres://user:password@host:port/dbname` |
| `REDIS_URL`            | Optional | Redis URL for cache and sessions |
| `MAPBOX_ACCESS_TOKEN`  | Optional | Mapbox token for the frontier map |

> [!NOTE]
> `PORT` and `RENDER_EXTERNAL_HOSTNAME` are injected automatically by Render. Senetrack dynamically adds the Render hostname to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

---

## 4. How Startup Works

Render invokes `Dockerfile` which runs [`scripts/start.sh`](file:///c:/Users/Little%20Human/Desktop/Django/Senetrack/scripts/start.sh):
1. **Static Files**: Pre-compiled during the Docker build step using WhiteNoise (`collectstatic`).
2. **Migrations**: `python manage.py migrate --noinput` runs automatically on start.
3. **Data Ingestion**: `python manage.py sync_performance --apply` hydrates Senator scores from JSON.
4. **Server**: Gunicorn starts bound to `0.0.0.0:${PORT}`.
