# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MoneyTracker is a full-stack personal finance application for a user based in Thailand. It tracks investments across multiple brokerages (Webull USA, Webull Thailand, Dime), banking transactions across Thai banks (Kasikorn, SCB, Bangkok Bank, Krungsri, Krungthai, TTB), and provides analytics on spending patterns, net worth, and portfolio performance.

## Architecture

- **Backend**: Python FastAPI (`backend/app/`) — async REST API with SQLAlchemy 2.0 async ORM
- **Frontend**: Next.js 15 + React 19 + Tailwind CSS 4 (`frontend/src/`)
- **Database**: PostgreSQL (via asyncpg for backend, psycopg2 for Celery workers)
- **Background Jobs**: Celery + Redis (`backend/app/workers/`)
- **File Parsing**: Modular parser system (`backend/app/parsers/`) — auto-detects institution from file content

## Common Commands

```bash
# Start all services
docker-compose up -d

# Backend only (local dev)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend only (local dev)
cd frontend && npm install && npm run dev

# Run database migrations
cd backend && alembic upgrade head

# Create a new migration
cd backend && alembic revision --autogenerate -m "description"

# Seed reference data (banks, brokerages, categories)
cd backend && python -m app.seed

# Start Celery worker
cd backend && celery -A app.workers.celery_app worker --loglevel=info

# Start Celery beat (scheduled tasks)
cd backend && celery -A app.workers.celery_app beat --loglevel=info
```

## Key Design Patterns

- **Parser auto-detection**: `backend/app/parsers/detector.py` tries specific parsers first (Kasikorn, SCB, Webull), falls back to generic CSV/PDF parsers. Each parser implements `can_parse()` and `parse()`.
- **Category inference**: `backend/app/services/categorizer.py` uses keyword matching (including Thai keywords) to auto-categorize bank transactions.
- **Backwards tracking**: `backend/app/services/history.py` reconstructs historical portfolio values by walking transaction history and joining with historical asset prices.
- **Cost basis tracking**: Holdings use running average cost basis, updated on each buy/sell via `_update_holding()` in `backend/app/workers/tasks.py`.
- **Statement processing is async**: Upload → create DB record → Celery task processes file → updates status. Frontend polls status.

## Data Flow

1. User uploads statement → `POST /api/statements/upload`
2. File saved, Statement record created as PENDING
3. Celery task `process_statement` picks it up
4. Parser auto-detected, transactions extracted
5. Bank txns auto-categorized, brokerage txns update holdings
6. For new assets, `fetch_historical_prices_for_asset` task triggered
7. Frontend fetches analytics via `/api/analytics/dashboard`

## API Prefix

All API routes are prefixed with `/api/`. Frontend proxies `/api/*` to backend via Next.js rewrites.
