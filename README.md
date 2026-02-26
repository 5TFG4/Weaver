# Weaver

> An automated trading system (live + backtesting) with a React UI.

<p align="center">
  <strong>&ensp;&ensp;&nbsp;&nbsp;&nbsp;[W]allE</strong><br/>
  <strong>&ensp;&nbsp;V[E]da</strong><br/>
  <strong>&nbsp;&nbsp;&nbsp;&nbsp;GL[A]DOS</strong><br/>
  <strong>Mar[V]in&ensp;&nbsp;</strong><br/>
  <strong>Gr[E]ta</strong><br/>
  <strong>Ha[R]o&ensp;</strong>
</p>

## Architecture

- **[Documentation Index](docs/DOCS_INDEX.md)** — Start here (document responsibilities + ownership)
- **[Architecture Overview](docs/ARCHITECTURE.md)** — System boundary, invariants, module map

| Detail Docs                                   |                                     |
| --------------------------------------------- | ----------------------------------- |
| [Events](docs/architecture/events.md)         | Event model, envelope, delivery     |
| [API](docs/architecture/api.md)               | REST, SSE, thin events              |
| [Clock](docs/architecture/clock.md)           | Realtime & backtest clocks          |
| [Config](docs/architecture/config.md)         | Credentials, security               |
| [Deployment](docs/architecture/deployment.md) | Docker, env vars                    |
| [Roadmap](docs/architecture/roadmap.md)       | High-level phases, entry checklists |

### ⚠️ Planning & Issue Tracking

| What                                              | Where                                                        |
| ------------------------------------------------- | ------------------------------------------------------------ |
| Current milestone plan & progress (authoritative) | [MILESTONE_PLAN.md](docs/MILESTONE_PLAN.md)                  |
| Active quality findings (authoritative)           | [DESIGN_AUDIT.md](docs/DESIGN_AUDIT.md)                      |
| Historical audit trail                            | [AUDIT_FINDINGS.md](docs/AUDIT_FINDINGS.md)                  |
| Historical detailed milestone docs                | [archive/milestone-details](docs/archive/milestone-details/) |

## Modules (brief)

- **GLaDOS** — Control plane & API (REST + SSE), domain routing, self‑clock.
- **Veda** — Live data & trading (exchange adapters, orders, caching).
- **Greta** — Backtesting (historical windows, fill/slippage/fees simulation).
- **Marvin** — Strategy execution (strategy intents & decisions).
- **WallE** — Persistence layer (centralized writes, repositories).
- **Haro** — React web UI (SSE for thin events, details via REST).

## Quickstart

### 1) Dev with Docker (recommended)

```bash
# from repository root
cp docker/example.env docker/.env

docker compose -f docker/docker-compose.dev.yml up --build
# API:     http://localhost:18919
# Frontend http://localhost:13579
```

### 2) “Prod-like” locally

```bash
docker compose -f docker/docker-compose.yml up -d --build
# API:     http://localhost:28919
# Frontend http://localhost:23579
```

### 3) Local (no Docker)

```bash
# Requires Python 3.13+
# backend
pip install -r docker/backend/requirements.txt
uvicorn weaver:app --host 0.0.0.0 --port 8000 --reload

# frontend (in ./haro)
npm install
npm run dev
```

## Development Status

| Milestone                  | Status           | Tests |
| -------------------------- | ---------------- | ----- |
| M0: Test Infrastructure    | ✅ Complete      | 14    |
| M0.5: Project Restructure  | ✅ Complete      | +74   |
| M1: Foundation (DB/Events) | ✅ Complete      | +124  |
| M2: API Live               | ✅ Complete      | +85   |
| M3: Veda Trading           | ✅ Complete      | +196  |
| M4: Greta Backtesting      | ✅ Complete      | +56   |
| M5: Marvin Core            | ✅ Complete      | +74   |
| M6: Live Trading           | ✅ Complete      | +101  |
| **M7: Haro Frontend**      | ✅ Complete      | +86   |
| **M8: Fixes & Improve**    | ✅ Complete      | +129  |

**Current Snapshot**: 1023 tests (933 backend + 90 frontend) · Coverage 89.61% · Python 3.13 · FastAPI · SQLAlchemy 2.x
**Authoritative milestone status**: [docs/MILESTONE_PLAN.md](docs/MILESTONE_PLAN.md)

### Recent Changes (2026-02-26)

- ✅ **M8 Complete**: Critical fixes, runtime wiring, code quality, and documentation (1023 total tests)
- ✅ All P0 critical issues resolved (SSE casing, start route, health path, order unification)
- ✅ Runtime pipeline wired (DomainRouter, PostgresEventLog dispatch, RunManager cleanup)
- ✅ Fills persistence + Runs recovery + AlpacaAdapter async wrapping
- ✅ Docker deployment blockers resolved (gunicorn, Dockerfile CMD, smoke tests)
- ✅ Architecture docs created (greta.md, marvin.md, walle.md)

### Next: M9 E2E & Release

- M9: end-to-end Playwright tests + deployment guide + release polish

## Endpoints (essentials)

- REST: `GET /api/v1/healthz`, `GET/POST /api/v1/runs`, `POST /api/v1/runs/{id}/start`, `GET /api/v1/orders`, `GET /api/v1/candles`
- Realtime: `GET /api/v1/events/stream` (SSE, supports `?run_id=` filtering)
