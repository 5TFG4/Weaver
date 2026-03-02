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

| Milestone                  | Status      | Tests |
| -------------------------- | ----------- | ----- |
| M0: Test Infrastructure    | ✅ Complete | 14    |
| M0.5: Project Restructure  | ✅ Complete | +74   |
| M1: Foundation (DB/Events) | ✅ Complete | +124  |
| M2: API Live               | ✅ Complete | +85   |
| M3: Veda Trading           | ✅ Complete | +196  |
| M4: Greta Backtesting      | ✅ Complete | +56   |
| M5: Marvin Core            | ✅ Complete | +74   |
| M6: Live Trading           | ✅ Complete | +101  |
| **M7: Haro Frontend**      | ✅ Complete | +86   |
| **M8: Fixes & Improve**    | ✅ Complete | +129  |

**Current Snapshot**: 1023 tests (933 backend + 90 frontend) · Coverage 89.61% · Python 3.13 · FastAPI · SQLAlchemy 2.x
**Authoritative milestone status**: [docs/MILESTONE_PLAN.md](docs/MILESTONE_PLAN.md)

### Recent Changes (2026-02-26)

- ✅ **M8 Complete**: Critical fixes, runtime wiring, code quality, and documentation (1023 total tests)
- ✅ All P0 critical issues resolved (SSE casing, start route, health path, order unification)
- ✅ Runtime pipeline wired (DomainRouter, PostgresEventLog dispatch, RunManager cleanup)
- ✅ Fills persistence + Runs recovery + AlpacaAdapter async wrapping
- ✅ Docker deployment blockers resolved (gunicorn, Dockerfile CMD, smoke tests)
- ✅ Architecture docs created (greta.md, marvin.md, walle.md)

### Next: M9 CI Deployment → M10 E2E & Release

- M9: CI deployment pipeline (backend/frontend fast lanes + compose smoke + merge gates)
- M10: end-to-end Playwright tests + deployment guide + release polish

## Local CI Smoke (Compose)

Run the same smoke flow as `.github/workflows/compose-smoke.yml` locally:

```bash
scripts/ci/compose-smoke-local.sh
```

Useful options:

```bash
# keep db/backend/frontend up for debugging after success
scripts/ci/compose-smoke-local.sh --keep-up

# faster rerun if images are already built
scripts/ci/compose-smoke-local.sh --no-build
```

What this script does:
- prepares `docker/.env` from `docker/example.env` (clears Alpaca keys for smoke)
- validates compose config and builds images
- starts `db`, runs `alembic upgrade head`, then starts `backend/frontend`
- checks `GET /api/v1/healthz` and frontend root page for HTTP 200
- tears down with `docker compose -f docker/docker-compose.yml down -v` (unless `--keep-up`)

## Testing Notes (Important)

- In this workspace, `runTests` is most reliable with:
  - relative paths (e.g., `tests/unit/glados/routes/test_runs.py`), or
  - `testNames` selectors.
- Absolute paths like `/weaver/tests/...` may return `No tests found` depending on runner path resolution.
- This is a tooling path-resolution behavior, not a project test failure.

## Endpoints (essentials)

- REST: `GET /api/v1/healthz`, `GET/POST /api/v1/runs`, `POST /api/v1/runs/{id}/start`, `GET /api/v1/orders`, `GET /api/v1/candles`
- Realtime: `GET /api/v1/events/stream` (SSE, supports `?run_id=` filtering)
