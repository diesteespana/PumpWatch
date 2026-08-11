# PumpWatch — Complete Deployment Guide

> **Audience:** You and your friend managing the server. No prior DevOps experience assumed.  
> **Domain:** `pumpwat.ch` (registered on GoDaddy)  
> **Stack:** Python / FastAPI · Next.js · PostgreSQL · Redis · Docker · nginx · Let's Encrypt

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [What You Need Before Starting](#2-what-you-need-before-starting)
3. [Server Setup (one-time)](#3-server-setup-one-time)
4. [GoDaddy DNS Configuration](#4-godaddy-dns-configuration)
5. [Clone the Repository](#5-clone-the-repository)
6. [Configure Environment Variables](#6-configure-environment-variables)
7. [Obtain SSL Certificates](#7-obtain-ssl-certificates)
8. [Deploy with Docker Compose](#8-deploy-with-docker-compose)
9. [Run Database Migrations](#9-run-database-migrations)
10. [Verify Everything Is Running](#10-verify-everything-is-running)
11. [Updating the App](#11-updating-the-app)
12. [Routine Maintenance](#12-routine-maintenance)
13. [Troubleshooting](#13-troubleshooting)
14. [Security Hardening Checklist](#14-security-hardening-checklist)

---

## 1. Architecture Overview

```
Internet
    │
    ▼
nginx (ports 80 + 443)  ← handles SSL termination, HSTS, HTTP→HTTPS redirect
    │
    ├──  pumpwat.ch  ──────────────►  frontend  (Next.js  :3000)
    │
    └──  api.pumpwat.ch  ──────────►  backend   (FastAPI  :8000)
                                            │
                                    PostgreSQL :5432
                                    Redis      :6379
```

All five services (`nginx`, `frontend`, `backend`, `db`, `redis`) run as Docker containers
on the same server and talk to each other over a private Docker network.
Only ports 80 and 443 are exposed to the outside world.

### What each piece does

| Service | Role |
|---------|------|
| **backend** | REST API, JWT auth, blockchain polling, scheduler, AI insights |
| **frontend** | Next.js dashboard — server-side rendered, served via node |
| **db** | PostgreSQL 16 — persists users, events, portfolios, strategies |
| **redis** | Caching (price oracle, AI results, rate limiter) |
| **nginx** | Reverse proxy, SSL, security headers |

---

## 2. What You Need Before Starting

### On your local machine
- Git installed
- Access to the GitHub repo (`https://github.com/diesteespana/PumpWatch`)
- GoDaddy account credentials for `pumpwat.ch`

### On the server (ask your friend to confirm)
- **OS:** Ubuntu 22.04 LTS or Debian 12 recommended
- **RAM:** 2 GB minimum, 4 GB recommended
- **Disk:** 20 GB free
- **Software:** Docker + Docker Compose (version 2.x, the one that uses `docker compose` not `docker-compose`)
- **Ports open in firewall:** 22 (SSH), 80 (HTTP), 443 (HTTPS)
- **A static public IP address** — you will need this for DNS

To check Docker is ready on the server:

```bash
docker --version          # should say Docker version 24+ or similar
docker compose version    # should say Docker Compose version v2.x
```

If Docker is not installed, your friend can run:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # allow your user to run docker without sudo
# log out and back in after this
```

---

## 3. Server Setup (one-time)

SSH into the server, then run these commands once. Everything after this is done through Docker.

```bash
# Update the system
sudo apt-get update && sudo apt-get upgrade -y

# Install essential tools
sudo apt-get install -y git curl certbot ufw fail2ban

# Firewall: allow SSH, HTTP, HTTPS only
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status

# Create a dedicated app directory
sudo mkdir -p /opt/pumpwatch
sudo chown $USER:$USER /opt/pumpwatch
```

> **Note for your friend:** The app will live at `/opt/pumpwatch`. All Docker data
> (PostgreSQL volumes, Redis data) is stored in named Docker volumes managed automatically.

---

## 4. GoDaddy DNS Configuration

This is the step that points the domain name at your server's IP address.

### Step-by-step

1. Log in to [godaddy.com](https://godaddy.com) → **My Products** → **DNS** next to `pumpwat.ch`
2. You will see a list of DNS records. You need to add or edit **three A records**.

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `@` | `YOUR_SERVER_IP` | 600 seconds |
| A | `www` | `YOUR_SERVER_IP` | 600 seconds |
| A | `api` | `YOUR_SERVER_IP` | 600 seconds |

- `@` means the root domain (`pumpwat.ch`)
- `www` handles `www.pumpwat.ch`
- `api` handles `api.pumpwat.ch` (the backend)

Replace `YOUR_SERVER_IP` with the actual IP address your friend gave you.

### Verify DNS has propagated (wait 5–30 minutes after saving)

```bash
# Run this from any machine
nslookup pumpwat.ch
nslookup api.pumpwat.ch
```

Both should return your server IP. Until they do, the SSL step will fail — so wait.

---

## 5. Clone the Repository

On the server, inside `/opt/pumpwatch`:

```bash
cd /opt/pumpwatch
git clone https://github.com/diesteespana/PumpWatch.git app
cd app
```

Your directory structure will now be:

```
/opt/pumpwatch/app/
├── backend/
├── frontend/
├── nginx/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── DEPLOYMENT.md  ← this file
```

---

## 6. Configure Environment Variables

The app reads all secrets from a `.env` file at the repo root. Never commit this file.

```bash
cp .env.example .env
nano .env    # or use vim, whichever you prefer
```

Fill in every value marked `change-me`. Here is what each one does:

### Required — must change before first run

```bash
# ── Application ───────────────────────────────────────────
APP_ENV=production
APP_SECRET_KEY=<generate below>
APP_DEBUG=false

# ── Database ──────────────────────────────────────────────
POSTGRES_PASSWORD=<generate below>
DATABASE_URL=postgresql+asyncpg://pumpwatch:<POSTGRES_PASSWORD>@db:5432/pumpwatch

# ── JWT ───────────────────────────────────────────────────
JWT_SECRET_KEY=<generate below>

# ── CORS ──────────────────────────────────────────────────
ALLOWED_ORIGINS=https://pumpwat.ch,https://www.pumpwat.ch
```

**Generate secure random secrets** (run these on the server, copy the output):

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"   # APP_SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"   # JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(24))"  # POSTGRES_PASSWORD
```

### Required — external API keys

```bash
# ── Blockchain ────────────────────────────────────────────
# Free at https://etherscan.io/myapikey
ETHERSCAN_API_KEY=your-key-here
ACTIVE_BLOCKCHAIN_PROVIDER=etherscan
```

### Optional but recommended

```bash
# ── AI (Claude) ───────────────────────────────────────────
# Get at https://console.anthropic.com
# Without this, the app falls back to rule-based heuristics (still works)
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL=claude-sonnet-5

# ── Notifications ─────────────────────────────────────────
# Telegram: create a bot via @BotFather on Telegram
TELEGRAM_BOT_TOKEN=

# Discord: Server Settings → Integrations → Webhooks
DISCORD_WEBHOOK_URL=

# Email (use your hosting provider's SMTP or a service like Resend/Mailgun)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@pumpwat.ch

# ── Price Oracle ──────────────────────────────────────────
# Free tier works (30 req/min). Pro key removes rate limits.
# https://www.coingecko.com/en/api
# COINGECKO_API_KEY=

# ── Trading Kill Switch ───────────────────────────────────
# Leave false until you have verified all risk rules are working correctly.
# The paper trading and strategy engine still run — only automated trade
# execution is blocked when this is false.
TRADING_ENABLED=false
```

### Frontend variables (must match the domain exactly)

```bash
NEXT_PUBLIC_API_URL=https://api.pumpwat.ch
NEXT_PUBLIC_APP_URL=https://pumpwat.ch
```

---

## 7. Obtain SSL Certificates

This uses Let's Encrypt (free, auto-renews every 90 days) to get HTTPS certificates
for all three subdomains at once.

**DNS must have propagated (Step 4) before running this.**

```bash
sudo certbot certonly \
  --standalone \
  -d pumpwat.ch \
  -d www.pumpwat.ch \
  -d api.pumpwat.ch \
  --email your@email.com \
  --agree-tos \
  --non-interactive
```

Certbot will place certificates at:
- `/etc/letsencrypt/live/pumpwat.ch/fullchain.pem`
- `/etc/letsencrypt/live/pumpwat.ch/privkey.pem`

These paths are already wired into `nginx/pumpwatch.conf` — no extra config needed.

### Auto-renewal setup

```bash
# Test that auto-renewal works
sudo certbot renew --dry-run

# Certbot installs a systemd timer automatically on Ubuntu.
# Confirm it is active:
sudo systemctl status certbot.timer
```

---

## 8. Deploy with Docker Compose

All commands run from `/opt/pumpwatch/app`.

### First deployment

```bash
# Build all images (takes 3–8 minutes on first run)
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start everything in the background
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Watch the logs to confirm startup
docker compose logs -f --tail=50
```

Press `Ctrl+C` to stop watching logs. The services keep running in the background.

### What happens on startup

1. `db` (PostgreSQL) starts and runs health checks
2. `redis` starts
3. `backend` waits for db + redis to be healthy, then starts FastAPI on port 8000
4. `frontend` starts Next.js on port 3000
5. `nginx` starts last and begins routing traffic from ports 80/443

---

## 9. Run Database Migrations

After the first `up -d`, the database tables do not exist yet. Run Alembic migrations
to create them:

```bash
docker compose exec backend alembic upgrade head
```

You should see output like:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, initial schema
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, paper trading
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003, strategy risk
```

**This command is safe to run again at any time** — Alembic skips already-applied migrations.
Run it again whenever you update the app (in case new migrations were added).

---

## 10. Verify Everything Is Running

### Check container health

```bash
docker compose ps
```

All containers should show `healthy` or `running` status. If any show `exited`, check logs:

```bash
docker compose logs backend
docker compose logs frontend
docker compose logs nginx
```

### Test the endpoints directly

```bash
# Backend health check
curl https://api.pumpwat.ch/health

# Expected response:
# {"status":"healthy","version":"0.1.0"}

# Frontend (just check for HTTP 200)
curl -o /dev/null -s -w "%{http_code}\n" https://pumpwat.ch
# Expected: 200
```

### Open in a browser

Visit `https://pumpwat.ch` — you should see the PumpWatch login page with a green padlock.

### Create your first account

Register at `https://pumpwat.ch/register` using your email address.

---

## 11. Updating the App

When new code is pushed to GitHub, deploy the update like this:

```bash
cd /opt/pumpwatch/app

# Pull latest code
git pull origin master

# Rebuild only changed images (Docker cache makes this fast)
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Replace running containers with zero-downtime restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Apply any new database migrations
docker compose exec backend alembic upgrade head
```

The entire update process typically takes under 2 minutes.

---

## 12. Routine Maintenance

### View live logs

```bash
docker compose logs -f backend       # API logs
docker compose logs -f frontend      # Next.js logs
docker compose logs -f nginx         # Access + error logs
```

### Restart a single service

```bash
docker compose restart backend
```

### Database backup

```bash
# Create a timestamped backup
docker compose exec db pg_dump -U pumpwatch pumpwatch \
  > /opt/pumpwatch/backups/pumpwatch_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker compose exec -T db psql -U pumpwatch pumpwatch \
  < /opt/pumpwatch/backups/pumpwatch_20260811_120000.sql
```

Set up automatic nightly backups:

```bash
sudo mkdir -p /opt/pumpwatch/backups
sudo crontab -e
```

Add this line (runs at 2 AM every day):

```
0 2 * * * cd /opt/pumpwatch/app && docker compose exec -T db pg_dump -U pumpwatch pumpwatch > /opt/pumpwatch/backups/pumpwatch_$(date +\%Y\%m\%d).sql 2>/dev/null
```

### Disk usage check

```bash
docker system df           # Docker images/volumes/containers
df -h /opt/pumpwatch       # Disk usage for app directory
```

### Clean up old Docker images

```bash
docker image prune -f      # Remove dangling images (safe, does not affect running containers)
```

---

## 13. Troubleshooting

### Site shows "502 Bad Gateway"

nginx is running but cannot reach the backend or frontend.

```bash
docker compose ps              # check all services are running
docker compose logs backend    # look for startup errors
docker compose logs frontend
```

Common cause: backend failed to start because the database is not ready. Fix:

```bash
docker compose restart backend
```

### "SSL certificate error" in browser

```bash
# Check certificate validity
sudo certbot certificates

# Force renewal if expired
sudo certbot renew --force-renewal

# Restart nginx to pick up new cert
docker compose restart nginx
```

### Database migration fails

```bash
# Check migration history
docker compose exec backend alembic history

# Check current revision
docker compose exec backend alembic current
```

If migrations are stuck, check for lock issues:

```bash
docker compose exec db psql -U pumpwatch -c "SELECT * FROM alembic_version;"
```

### Backend won't start — "ValidationError: Field required"

Your `.env` file is missing a required variable. Check:

```bash
docker compose exec backend python -c "from app.core.config import get_settings; get_settings()"
```

The error message will name the missing field.

### Frontend shows blank page / JS errors

Build-time environment variables were not baked in. Rebuild the frontend:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build frontend
docker compose up -d frontend
```

### "Too many redirects" in browser

Usually means the nginx SSL config is not terminating TLS properly, or
`ALLOWED_ORIGINS` in `.env` does not include `https://pumpwat.ch` (with https).

### Check if nginx config is valid before restarting

```bash
docker compose exec nginx nginx -t
```

---

## 14. Security Hardening Checklist

Run through this before going live.

- [ ] All secrets in `.env` are long random strings (not the `change-me` placeholders)
- [ ] `APP_DEBUG=false` in production `.env`
- [ ] `TRADING_ENABLED=false` (leave it off until you are certain risk rules work)
- [ ] PostgreSQL and Redis ports are **not** exposed to the internet (confirmed in `docker-compose.prod.yml`)
- [ ] Firewall allows only ports 22, 80, 443 (`sudo ufw status`)
- [ ] SSH key-based auth is set up; password login is disabled:
  ```bash
  # On server
  sudo nano /etc/ssh/sshd_config
  # Set: PasswordAuthentication no
  sudo systemctl restart sshd
  ```
- [ ] fail2ban is running (protects SSH from brute force):
  ```bash
  sudo systemctl status fail2ban
  ```
- [ ] SSL certificate is valid and auto-renewal timer is active (`sudo systemctl status certbot.timer`)
- [ ] HSTS header is present (checked automatically by nginx config)
- [ ] Backups are scheduled and have been tested by doing a restore

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Start everything | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` |
| Stop everything | `docker compose down` |
| View all logs | `docker compose logs -f` |
| Run migrations | `docker compose exec backend alembic upgrade head` |
| Deploy update | `git pull && docker compose ... build && docker compose ... up -d` |
| Backup database | `docker compose exec db pg_dump -U pumpwatch pumpwatch > backup.sql` |
| Restart backend | `docker compose restart backend` |
| Check containers | `docker compose ps` |
| Check SSL cert | `sudo certbot certificates` |
| Renew SSL cert | `sudo certbot renew` |
| Test nginx config | `docker compose exec nginx nginx -t` |

---

## Project File Map

```
pumpwat.ch/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/     REST endpoints (auth, wallets, alerts, tokens,
│   │   │                       paper-trading, strategy, analytics)
│   │   ├── ai/                 Claude-powered insights + heuristic fallback
│   │   ├── blockchain/         Etherscan provider, price oracle (CoinGecko)
│   │   ├── core/               config.py (all env vars), logging, exceptions
│   │   ├── database/           SQLAlchemy async engine, session factory
│   │   ├── events/             Detection engine + 13 event classifiers
│   │   ├── models/             ORM models (User, Event, Alert, Paper Trading, Strategy…)
│   │   ├── notifications/      Telegram / Discord / Email channels
│   │   ├── repositories/       DB query layer (no raw SQL in services)
│   │   ├── schemas/            Pydantic v2 request/response models
│   │   ├── services/           Business logic (paper trading, strategy engine,
│   │   │                       risk management, analytics, detection)
│   │   ├── scheduler.py        APScheduler jobs (blockchain poll, AI insights,
│   │   │                       strategy engine, risk checks)
│   │   └── main.py             FastAPI app + router registration
│   ├── alembic/versions/       3 migrations: initial → paper trading → strategy+risk
│   ├── tests/                  Unit tests (28 test files, 18 new in M10/M11)
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── app/                Next.js App Router pages
│       │   └── dashboard/      Overview, Wallets, Alerts, Tokens, Rankings,
│       │                       Paper Trading, Settings
│       ├── components/         UI primitives + layout (Sidebar, Header, EventFeed…)
│       ├── hooks/              React Query hooks for every backend endpoint
│       ├── lib/                axios instance (JWT interceptor), queryClient
│       └── types/api.ts        TypeScript interfaces matching backend schemas
├── nginx/pumpwatch.conf        Reverse proxy config (HTTP→HTTPS, subdomains, HSTS)
├── docker-compose.yml          Base compose (dev)
├── docker-compose.prod.yml     Production overrides (no source mounts, nginx service)
├── .env.example                Template for .env — copy and fill in
└── .github/workflows/ci.yml    GitHub Actions: lint + test + docker build on push
```

---

*Last updated: 2026-08-11 — All 11 milestones complete. Backend at commit `be3432c`.*
