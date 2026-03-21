# Push Senetrack to GitHub

Your code is committed locally but not yet on [github.com/MukoyaKuya/Senetrack](https://github.com/MukoyaKuya/Senetrack). Push it from your machine (Git will ask for your credentials).

## Option 1: HTTPS with Personal Access Token (easiest)

1. **Create a token on GitHub**
   - Go to: https://github.com/settings/tokens
   - Click **"Generate new token (classic)"**
   - Name it (e.g. "Senetrack push"), enable **repo**, then generate and **copy the token**.

2. **Push from your project folder**
   ```powershell
   cd "C:\Users\Little Human\Desktop\ReportFormv2"
   git push -u origin main
   ```
   - **Username:** your GitHub username (e.g. `MukoyaKuya`)
   - **Password:** paste the **token** (not your GitHub account password)

After this, refresh https://github.com/MukoyaKuya/Senetrack and you should see all files.

## Option 2: GitHub CLI

If you have [GitHub CLI](https://cli.github.com/) installed:

```powershell
cd "C:\Users\Little Human\Desktop\ReportFormv2"
gh auth login
git push -u origin main
```

## Option 3: SSH

If you use SSH keys with GitHub:

```powershell
cd "C:\Users\Little Human\Desktop\ReportFormv2"
git remote set-url origin git@github.com:MukoyaKuya/Senetrack.git
git push -u origin main
```

---

If you get "failed to push" or "rejected", say what error you see and we can fix it.
