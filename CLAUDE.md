# PumpWatch — Project Brief for Claude Code

## What This Is
PumpWatch (`pumpwat.ch`) is a production-grade on-chain analytics SaaS.
Vision: Bloomberg Terminal for on-chain intelligence.

## Milestones
| # | Scope | Status |
|---|-------|--------|
| 1 | Scaffold, Docker, CI/CD, CLAUDE.md | ✅ Done |
| 2 | Blockchain abstraction layer + Etherscan impl | ✅ Done |
| 3 | DB models, repositories, Alembic migrations | ⬜ |
| 4 | Detection engine + event classification | ⬜ |
| 5 | Notification engine (Telegram, Discord, Email) | ⬜ |
| 6 | REST API + Auth (JWT/refresh) | ⬜ |
| 7 | Next.js dashboard | ⬜ |
| 8 | Wallet intelligence + historical analytics | ⬜ |
| 9 | AI architecture + prediction interfaces | ⬜ |
| 10 | Paper trading simulator | ⬜ |
| 11 | Automated exchange execution + risk mgmt | ⬜ |

## Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, Alembic, APScheduler
- **Frontend**: Next.js (App Router), TypeScript, TailwindCSS, Recharts
- **DB**: PostgreSQL
- **Infra**: Docker, Docker Compose, GitHub Actions

## Key Architecture Decisions
1. **Provider abstraction**: All blockchain calls go through `BlockchainProvider` interface → swap Etherscan→Alchemy etc. without touching business logic
2. **Repository pattern**: No raw queries in services; all DB access via typed repository classes
3. **Event engine**: Extensible `BaseEvent` → typed subclasses, not a single "large transfer" check
4. **Notification interface**: `NotificationChannel` ABC → add Slack/SMS/Webhook without changing callers
5. **Auth**: JWT + refresh tokens, OAuth-ready (no provider lock-in)
6. **AI-ready**: `WalletScorer` and `MarketInsightEngine` interfaces defined even when unimplemented

## Folder Layout
```
pumpwatch/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/
│   │   ├── auth/
│   │   ├── blockchain/providers/
│   │   ├── core/          # config, logging, security constants
│   │   ├── database/
│   │   ├── events/        # detection engine
│   │   ├── models/        # SQLAlchemy ORM
│   │   ├── notifications/
│   │   ├── repositories/
│   │   ├── schemas/       # Pydantic v2
│   │   ├── services/
│   │   └── utils/
│   ├── alembic/
│   └── tests/
└── frontend/
    └── src/
        ├── app/           # Next.js App Router pages
        ├── components/
        ├── lib/
        └── types/
```

## Coding Standards
- Full type hints everywhere
- Dependency injection via FastAPI `Depends`
- SOLID principles; no magic numbers (use `core/constants.py`)
- No duplicated logic; no placeholder implementations
- pytest + Playwright; target 90%+ coverage
- All secrets via env vars; never hardcoded

## Event Types (Detection Engine)
WhaleBuy, WhaleSell, ExchangeDeposit, ExchangeWithdrawal, LiquidityAdded,
LiquidityRemoved, ContractDeployment, TokenMint, TokenBurn, LargeSwap,
SmartMoneyActivity, WalletAccumulation, WalletDistribution

Each event carries: timestamp, blockchain, token, tx_hash, wallet, usd_value,
confidence_score, event_type, explanation

## To Continue a Session
Tell Claude: "Continue PumpWatch at Milestone N" — CLAUDE.md provides all context.
Mark milestone status above as ✅ when done.
