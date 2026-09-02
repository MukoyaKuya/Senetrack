# Deploy Senetrack on AWS Free Tier (HTTP + public IP)

> **Preferred free host:** Oracle Always Free — see [`ORACLE_FREE_TIER.md`](ORACLE_FREE_TIER.md). Use this AWS guide only if you specifically want AWS.

This guide gets Senetrack running at `http://<ec2-public-ip>` with **no custom domain** and **no HTTPS**. It reuses your existing **Neon Postgres** and **Cloudinary** accounts so you avoid paid AWS database/storage.

You need: this repo, Neon `DATABASE_URL`, Cloudinary keys, and a new AWS account.

---

## 1. Create an AWS account

1. Go to [https://aws.amazon.com/free/](https://aws.amazon.com/free/) and create an account.
2. Choose the **Free** plan if offered (new accounts get limited free credits / free-tier eligible instances for a fixed period).
3. Complete phone and payment verification (a card is usually required; free-plan usage should not bill if you stay within limits — still set a budget alert).
4. In the console: **Billing → Budgets → Create budget** (e.g. $1–$5) with email alerts at 80% and 100%.

Pick a region close to users (e.g. `eu-west-1` or `us-east-1`) and use it for every step below.

---

## 2. Create a key pair

1. **EC2 → Key pairs → Create key pair**
2. Name: `senetrack`
3. Type: RSA, format: `.pem` (Linux/Mac) or `.ppk` if you use PuTTY on Windows
4. Download and store the file safely (you cannot download it again)

---

## 3. Security group

1. **EC2 → Security groups → Create security group**
2. Name: `senetrack-web`
3. Inbound rules:

| Type | Port | Source | Why |
|------|------|--------|-----|
| SSH | 22 | My IP | Admin access only from you |
| HTTP | 80 | Anywhere `0.0.0.0/0` | Public site |

4. Outbound: leave default (all)

---

## 4. Launch a free-tier EC2 instance

1. **EC2 → Launch instance**
2. Name: `senetrack`
3. AMI: **Ubuntu Server 24.04 LTS** (or latest Ubuntu marked free-tier eligible)
4. Instance type: free-tier eligible (often `t3.micro` or `t4g.micro` — prefer what the console marks **Free tier eligible**)
5. Key pair: `senetrack`
6. Network: select security group `senetrack-web`
7. Storage: **8–20 GB gp3** (stay within free-tier disk limits)
8. Launch, then copy the **Public IPv4 address**

---

## 5. SSH in and install Docker

**Linux / macOS / Windows (OpenSSH):**

```bash
ssh -i /path/to/senetrack.pem ubuntu@YOUR_PUBLIC_IP
```

On the instance:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker ubuntu
```

Log out and SSH back in so the `docker` group applies. Confirm:

```bash
docker run --rm hello-world
```

---

## 6. Get the code onto the instance

**Option A — GitHub (preferred):**

```bash
sudo apt-get install -y git
git clone https://github.com/YOUR_USER/Senetrack.git
cd Senetrack
```

**Option B — copy from your PC** (from your machine):

```bash
scp -i /path/to/senetrack.pem -r /path/to/Senetrack ubuntu@YOUR_PUBLIC_IP:~/
```

Then on the instance: `cd ~/Senetrack`

---

## 7. Create the env file on the instance

```bash
nano .env
```

Use values from `.env.example`. Minimum:

```env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=paste-a-long-random-string-here
ALLOWED_HOSTS=YOUR_PUBLIC_IP
DATABASE_URL=postgresql://...neon.../neondb?sslmode=require
USE_CLOUDINARY=true
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
SECURE_SSL_REDIRECT=false
PORT=8080
GUNICORN_WORKERS=1
```

Replace `YOUR_PUBLIC_IP` with the real EC2 IP (no `http://`).

Generate a secret key on the instance if needed:

```bash
openssl rand -base64 48
```

Do **not** set `REDIS_URL` on free tier.

---

## 8. Build and run

```bash
docker build -t senetrack .
docker run -d --name senetrack \
  --env-file .env \
  -p 80:8080 \
  --restart unless-stopped \
  senetrack
```

Watch logs:

```bash
docker logs -f senetrack
```

You should see migrations, then Gunicorn starting on `0.0.0.0:8080`.

Optional faster boots (skip performance JSON sync):

```bash
docker run -d --name senetrack \
  --env-file .env \
  -e SKIP_SYNC_PERFORMANCE=true \
  -p 80:8080 \
  --restart unless-stopped \
  senetrack
```

---

## 9. Verify

On your laptop browser open:

```text
http://YOUR_PUBLIC_IP
```

Checks:

- Home page loads
- CSS/JS load (WhiteNoise)
- Senator images load (Cloudinary)
- Admin path works if you set `DJANGO_ADMIN_PATH`

If you get `DisallowedHost`, fix `ALLOWED_HOSTS` to match the IP exactly and recreate the container.

If the browser redirects to HTTPS and fails, ensure `SECURE_SSL_REDIRECT=false` and recreate the container.

---

## 10. Rotate the Neon password (required)

An older copy of `scripts/direct_sql_import.py` contained a Neon password in plain text. Even after removal from the repo:

1. Neon console → reset/rotate the database password
2. Update `DATABASE_URL` in the EC2 `.env`
3. Restart: `docker restart senetrack`

---

## Useful commands

```bash
docker logs -f senetrack
docker restart senetrack
docker stop senetrack && docker rm senetrack
# rebuild after code changes
docker build -t senetrack . && docker rm -f senetrack
docker run -d --name senetrack --env-file .env -p 80:8080 --restart unless-stopped senetrack
```

---

## Cost control checklist

- One free-tier **micro** instance only
- No RDS, ElastiCache, ALB, or Elastic IP unless you accept charges (Elastic IP can cost money when not attached)
- Stop or terminate the instance when you are done experimenting
- Keep the billing budget alert on

---

## Later (out of scope here)

- Custom domain + HTTPS (Nginx/Caddy + Certbot)
- Elastic Beanstalk for managed deploys
- Moving media to S3
