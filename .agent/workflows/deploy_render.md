---
description: How to deploy the Senetrack application to Render (render.com)
---

Follow these steps to deploy Senetrack to Render using Docker.

### 1. Push Changes to GitHub

Render builds directly from your GitHub repository:

```bash
git add .
git commit -m "feat: configure render deployment"
git push origin main
```

### 2. Create Service on Render

#### Option A: One-Click via Render Blueprint (Recommended)
1. Go to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub repository (`MukoyaKuya/Senetrack`).
4. Render detects `render.yaml` and prepares the Web Service.
5. Provide values for required environment variables (see below) and click **Apply**.

#### Option B: Manual Web Service
1. Go to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository.
4. Set the following settings:
   - **Name**: `senetrack`
   - **Language**: `Docker`
   - **Branch**: `main`
   - **Region**: Oregon or Frankfurt
   - **Plan**: Free (or Starter)
   - **Health Check Path**: `/`

### 3. Required Environment Variables

Set these in the **Environment** tab on Render:

| Variable | Recommended Value | Notes |
| :--- | :--- | :--- |
| `DJANGO_DEBUG` | `false` | Must be `false` in production |
| `DJANGO_SECRET_KEY` | *(Generate a 50+ char random string)* | Required |
| `SECURE_SSL_REDIRECT` | `true` | Enforces HTTPS |
| `USE_CLOUDINARY` | `true` | Serves media assets from Cloudinary |
| `CLOUDINARY_CLOUD_NAME` | *(Your Cloudinary Cloud Name)* | e.g. `dlj4gpozf` |
| `CLOUDINARY_API_KEY` | *(Your Cloudinary API Key)* | From Cloudinary dashboard |
| `CLOUDINARY_API_SECRET` | *(Your Cloudinary API Secret)* | From Cloudinary dashboard |
| `DATABASE_URL` | *(Optional PostgreSQL connection string)* | If not set, container SQLite is used |
| `MAPBOX_ACCESS_TOKEN` | *(Optional Mapbox token)* | For interactive frontier map |

> [!TIP]
> `PORT` and `RENDER_EXTERNAL_HOSTNAME` are automatically set by Render. Django will automatically add your `*.onrender.com` domain to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

### 4. Automatic Startup & Migrations

During container launch, Render runs `scripts/start.sh`, which automatically:
1. Runs database migrations (`python manage.py migrate --noinput`).
2. Syncs Senator performance data (`python manage.py sync_performance --apply`).
3. Binds Gunicorn to the Render-assigned port (`0.0.0.0:${PORT}`).

### 5. Verification

Once the build and deploy logs show `Starting Gunicorn...`, open your live Render URL:
`https://<your-service-name>.onrender.com`
