---
description: How to deploy the Senetrack application to Google Cloud Run and sync with GitHub
---

Follow these steps to ensure the application is correctly updated on both GitHub and Google Cloud Run.

### 1. Synchronize with GitHub

Always push your changes to GitHub before deploying to ensure the remote repository is the source of truth.

```bash
# Add all changes
git add .

# Commit changes with a descriptive message
git commit -m "feat: your descriptive message"

# Push to the main branch
git push origin main
```

### 2. Deploy to Google Cloud Run

The application is hosted on Google Cloud Run and uses a `Dockerfile` for containerization.

// turbo
```bash
gcloud run deploy senetrack --region us-east1 --source . --quiet
```

### 3. Verification

After deployment, verify the changes on the live site:
- **URL**: [https://senetrack-1073897174388.us-east1.run.app/](https://senetrack-1073897174388.us-east1.run.app/)

### Troubleshooting

- **Database Migrations**: Migrations are handled automatically by `scripts/start.sh` during container startup.
- **Static Files**: `collectstatic` is also handled by `scripts/start.sh`.
- **Environment Variables**: Ensure sensitive variables are managed in the Google Cloud Console or via Secret Manager if needed.
