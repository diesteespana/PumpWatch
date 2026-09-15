# PumpWatch

**On-chain analytics for people who need to know what moved, and when.**

PumpWatch watches blockchain wallets, classifies what they do into meaningful events — a whale
buying, liquidity being pulled, money walking onto an exchange — scores the wallets behind those
events, and tells you about it through the channel you actually read.

[![CI](https://github.com/diesteespana/PumpWatch/actions/workflows/ci.yml/badge.svg)](https://github.com/diesteespana/PumpWatch/actions/workflows/ci.yml)

> **Status:** in active development. All eleven planned milestones are implemented and tested
> locally; the platform has not been deployed to production yet. Automated trading ships behind a
> kill switch that is **off** by default (`TRADING_ENABLED=false`).

---

## What it does

| | |
|---|---|
| **Watches wallets** | Polls a blockchain provider on a schedule, enriches raw transfers with token metadata and USD value, and stores what it finds. |
| **Classifies events** | Thirteen event types — whale buys and sells, exchange deposits and withdrawals, liquidity added and removed, contract deployments, mints and burns, large swaps, smart-money activity, accumulation and distribution. |
| **Scores wallets** | A heuristic score out of 100 built from volume, activity, token diversity and recency, persisted and ranked into a leaderboard. |
| **Explains what happened** | Optional AI layer (Claude) that writes wallet insights and market commentary, with a heuristic fallback when no API key is configured. Every result is cached in Redis. |
| **Notifies** | Telegram, Discord and email, behind one interface and a rate limiter. |
| **Simulates and executes** | Paper-trading portfolio, a strategy builder, and exchange execution with position-size and risk limits. |

The dashboard gives you an overview with a live event feed, a per-wallet detail page with volume
over time and a score breakdown, a rankings table, token signals, and alert configuration.

---

## Architecture

The interesting part of this project is not the feature list, it is what the features are allowed
to depend on.

**Everything external sits behind an interface.** The blockchain provider, the notification channel,
the event classifier, the wallet scorer and the market-insight engine are all abstract base classes
with concrete implementations chosen by a factory. Swapping Etherscan for Alchemy, or adding Slack
alongside Telegram, does not touch a line of business logic.

**No raw queries outside the repository layer.** Every table is reached through a typed repository
extending a generic `BaseRepository[T]`; services compose repositories and never see a session.

**`EnrichedTransfer` is the contract** between the blockchain layer and the detection engine — the
single handoff type that keeps "how we got the data" separate from "what the data means".

**AI calls are lazy and cached.** They run on demand from the API, never from the scheduler, and
every response is cached in Redis (5 minutes for signals, 30 for market insight, 1 hour for wallet
scores). An AI outage degrades the product to heuristics instead of taking it down.

```
backend/app/
├── blockchain/     # BlockchainProvider ABC + Etherscan implementation
├── events/         # EventClassifier, DetectionEngine, threshold config
├── notifications/  # NotificationChannel ABC, channels/, rate limiter, formatter
├── ai/             # PredictionEngine, wallet scorer, market insight, factory
├── repositories/   # BaseRepository[T] and one repository per model
├── services/       # Business logic: analytics, detection, strategy, risk
├── api/v1/routers/ # auth · users · wallets · events · alerts · tokens ·
│                   # analytics · notifications · paper_trading · strategy
├── models/         # SQLAlchemy models (16 tables)
├── schemas/        # Pydantic v2 request/response schemas
└── scheduler.py    # APScheduler jobs: polling, scoring, strategies
```

---

## Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2 (async), Pydantic v2, Alembic, APScheduler |
| **Frontend** | Next.js 14 (App Router), TypeScript, TailwindCSS, React Query, Zustand, Recharts |
| **Data** | PostgreSQL 16, Redis |
| **Auth** | JWT access tokens + rotating refresh tokens, OAuth-ready |
| **Infra** | Docker Compose, Nginx, GitHub Actions |
| **Tests** | pytest (195 unit tests), Playwright (end-to-end) |

---

## Quick start

You need Docker and Docker Compose. Nothing else.

```bash
git clone https://github.com/diesteespana/PumpWatch.git
cd PumpWatch
cp .env.example .env        # then fill in ETHERSCAN_API_KEY at minimum
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Or use the helper, which does both steps:

```bash
./scripts/dev.sh
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |

Apply database migrations:

```bash
docker compose exec backend alembic upgrade head
```

### Configuration

Everything is environment-driven; `.env.example` documents all of it. The variables that matter
most:

| Variable | Why it matters |
|---|---|
| `ETHERSCAN_API_KEY` | Required. Without it there is no on-chain data to classify. |
| `APP_SECRET_KEY`, `JWT_SECRET_KEY` | Must be changed before anything leaves your laptop. |
| `WHALE_THRESHOLD_USD` | The USD line above which a transfer becomes a whale event. |
| `BLOCKCHAIN_POLL_INTERVAL_SECONDS` | How often the scheduler polls. Mind your rate limits. |
| `ANTHROPIC_API_KEY` | Optional. Unset means the AI layer falls back to heuristics. |
| `TELEGRAM_BOT_TOKEN`, `DISCORD_WEBHOOK_URL`, `SMTP_*` | Notification channels; configure only the ones you want. |
| `TRADING_ENABLED` | Kill switch for automated execution. Leave it `false` unless you mean it. |

---

## Tests

```bash
cd backend && pytest                    # 195 unit tests
cd frontend && npx playwright test      # end-to-end
```

CI runs backend lint and tests, frontend lint and type checking, and a Docker build check on every
push.

---

## Why it exists

I built PumpWatch to find out what a production-grade system actually demands once you stop writing
scripts and start writing something other people could run: migrations that apply cleanly, secrets
that never reach the repository, a test suite you trust enough to refactor behind, interfaces that
survive a change of vendor, and a kill switch on the part that can lose money.

Built by [Nicolás Dieste España](https://github.com/diesteespana).
