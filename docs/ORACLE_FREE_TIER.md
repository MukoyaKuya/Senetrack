# Deploy Senetrack on Oracle Cloud Always Free (HTTP + public IP)

This guide runs Senetrack at `http://<oracle-public-ip>` with **no custom domain** and **no HTTPS**. It reuses **Neon Postgres** and **Cloudinary** so you do not need Oracle Autonomous DB or Object Storage.

You need: this repo, Neon `DATABASE_URL`, Cloudinary keys, and an Oracle Cloud account.

**Why Oracle:** Always Free Ampere VMs stay free (not a short trial). More RAM than a typical AWS free micro, so Django + Gunicorn is comfortable.

---

## 1. Create an Oracle Cloud account

1. Go to [https://www.oracle.com/cloud/free/](https://www.oracle.com/cloud/free/) and sign up.
2. Pick a home region you will keep (you cannot change it later easily). Prefer a region that still has Ampere capacity (e.g. some EU/US regions fill up).
3. Complete email, phone, and card verification (card is required; Always Free should not charge if you only use free shapes).
4. Set a budget alert in **Billing & Cost Management** (e.g. $1) so you notice any accidental paid resources.

---

## 2. Create an Always Free Ampere VM

1. Console → **Compute → Instances → Create instance**
2. Name: `senetrack`
3. **Image:** Canonical Ubuntu 22.04 or 24.04 (ARM / aarch64 compatible)
4. **Shape:** Change shape → **Ampere** → `VM.Standard.A1.Flex` (Always Free eligible)
5. Suggested size for Senetrack:
   - **1 OCPU / 6 GB RAM** (plenty for this app), or
   - **2 OCPU / 12 GB RAM** if you want headroom  
   Avoid requesting more than your tenancy’s Always Free Ampere quota (often **2 OCPU / 12 GB total** across all A1 instances — check the console if create fails).
6. **Networking:** assign a **public IPv4** address
7. **SSH keys:** paste your public key (or generate one)
8. Create the instance and copy the **Public IP**

If Ampere is “out of capacity”, try another AD/region or retry later. Do **not** pick paid shapes.

---

## 3. Open ports in OCI (cloud firewall)

Oracle blocks inbound traffic by default. You must allow SSH and HTTP in the VCN security list:

1. **Networking → Virtual Cloud Networks →** your VCN  
2. **Security Lists → Default Security List** (or the list on your subnet)  
3. **Add Ingress Rules:**

| Source CIDR | Protocol | Dest port | Purpose |
|-------------|----------|-----------|---------|
| `YOUR_HOME_IP/32` | TCP | 22 | SSH (lock to your IP) |
| `0.0.0.0/0` | TCP | 80 | Public HTTP |

Leave SSH open to `0.0.0.0/0` only if you accept that risk.

---

## 4. SSH in and open the OS firewall

```bash
ssh -i /path/to/your_key ubuntu@YOUR_PUBLIC_IP
```

Ubuntu images on OCI often need **iptables** as well as the security list:

```bash
sudo iptables -I INPUT -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo apt-get update
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

(If you use `ufw` instead, allow `OpenSSH` and `80/tcp`, then enable ufw.)

---

## 5. Install Docker (on the ARM instance)

Build **on the Oracle VM**. Ampere is **ARM64** — do not copy an x86 image built on a typical Windows/Intel laptop.

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker ubuntu
```

Log out and SSH back in, then:

```bash
docker run --rm hello-world
uname -m
# expect: aarch64
```

---

## 6. Get the code

```bash
git clone https://github.com/YOUR_USER/Senetrack.git
cd Senetrack
```

Or `scp` the project from your PC (exclude local `media/` if possible — `.dockerignore` already excludes it from the image).

---

## 7. Create `.env` on the instance

```bash
nano .env
```

Minimum (see `.env.example`):

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
GUNICORN_WORKERS=2
```

Generate a secret:

```bash
openssl rand -base64 48
```

Do **not** set `REDIS_URL` unless you run Redis yourself.

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

Logs:

```bash
docker logs -f senetrack
```

Optional faster boot:

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

Open:

```text
http://YOUR_PUBLIC_IP
```

Checks: home page, CSS/JS (WhiteNoise), images (Cloudinary).

| Symptom | Fix |
|---------|-----|
| Connection timeout | Security list + iptables for port 80 |
| `DisallowedHost` | Set `ALLOWED_HOSTS` to the public IP; recreate container |
| HTTPS redirect loop/fail | `SECURE_SSL_REDIRECT=false`; recreate container |
| OOM / crash | Lower `GUNICORN_WORKERS` to `1` |

---

## 10. Rotate Neon password

If the Neon password was ever committed in this repo, rotate it in the Neon console, update `DATABASE_URL` on the VM, then:

```bash
docker restart senetrack
```

---

## Useful commands

```bash
docker logs -f senetrack
docker restart senetrack
docker rm -f senetrack
docker build -t senetrack . && docker run -d --name senetrack --env-file .env -p 80:8080 --restart unless-stopped senetrack
```

---

## Cost control

- Use only **Always Free** Ampere (`VM.Standard.A1.Flex`) — never upgrade to paid shapes “just to get capacity”
- Do not create paid Load Balancers, Databases, or extra large block volumes beyond free limits
- Keep the budget alert on
- One public IP + one VM is enough for this phase

---

## Later (out of scope)

- Domain + HTTPS (Caddy/Nginx + Let’s Encrypt on the same VM)
- Opening port 443 in security list + iptables
- Moving off Neon/Cloudinary onto Oracle services

---

## vs AWS free tier

| | Oracle Always Free | AWS free tier |
|--|--------------------|---------------|
| Duration | Ongoing Always Free | Limited free period / credits |
| RAM | 6–12+ GB easy | ~1 GB micro |
| Arch | ARM64 (build on VM) | Usually x86 |
| Hard part | Signup + capacity + dual firewalls | Billing after free window |

Prefer this Oracle guide for Senetrack’s long-term free hosting.
