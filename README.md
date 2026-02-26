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
| M8: Fixes & Improve        | 🔄 Active (M8-R) | 96+   |

**Current Snapshot**: 998 tests (908 backend + 90 frontend) · Coverage 89.78% · Python 3.13 · FastAPI · SQLAlchemy 2.x
**Authoritative milestone status**: [docs/MILESTONE_PLAN.md](docs/MILESTONE_PLAN.md)

### Recent Changes (2026-02-04)

- ✅ **M6 Complete**: Live trading system with plugin adapter architecture (808 total tests)
- ✅ PluginAdapterLoader with AST-based discovery (40 tests)
- ✅ AlpacaAdapter connection management with connect/disconnect/is_connected (23 tests)
- ✅ VedaService wired to order routes for live order creation (13 tests)
- ✅ Live order flow with persistence and event emission (15 tests)
- ✅ RealtimeClock integration for live/paper runs (10 tests)
- ✅ Comprehensive Veda trading documentation (`docs/architecture/veda.md`)

### Next: M8-R Closeout → M9 E2E

- M8-R: deployment blockers + runtime/doc consistency closeout
- M9: end-to-end test execution and release polish

## Endpoints (essentials)

- REST: `GET /api/v1/healthz`, `GET/POST /api/v1/runs`, `GET /api/v1/orders`, `GET /api/v1/candles`
- Realtime: `GET /api/v1/events/stream` (SSE)
