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

* **[Architecture Overview](docs/ARCHITECTURE.md)** — Start here (includes planning doc index)

| Detail Docs | |
|-------------|---|
| [Events](docs/architecture/events.md) | Event model, envelope, delivery |
| [API](docs/architecture/api.md) | REST, SSE, thin events |
| [Clock](docs/architecture/clock.md) | Realtime & backtest clocks |
| [Config](docs/architecture/config.md) | Credentials, security |
| [Deployment](docs/architecture/deployment.md) | Docker, env vars |
| [Roadmap](docs/architecture/roadmap.md) | Milestones, entry checklists |

### ⚠️ Planning & Issue Tracking

| What | Where |
|------|-------|
| Issue backlog & milestone schedule | [AUDIT_FINDINGS.md §5-6](docs/AUDIT_FINDINGS.md#5-milestone-based-fix-schedule) |
| Current milestone design | [M6 Live Trading (Complete)](docs/archive/milestone-details/m6-live-trading.md) |
| Next milestone | M7: Haro Frontend |



## Modules (brief)

* **GLaDOS** — Control plane & API (REST + SSE), domain routing, self‑clock.
* **Veda** — Live data & trading (exchange adapters, orders, caching).
* **Greta** — Backtesting (historical windows, fill/slippage/fees simulation).
* **Marvin** — Strategy execution (strategy intents & decisions).
* **WallE** — Persistence layer (centralized writes, repositories).
* **Haro** — React web UI (SSE for thin events, details via REST).



## Quickstart

### 1) Dev with Docker (recommended)

```bash
# from repository root
cp .env.example .env
cp .env.dev.example .env.dev

docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build
# API:     http://localhost:8000
# Frontend http://localhost:3000
```

### 2) “Prod-like” locally

```bash
docker compose -f docker/docker-compose.yml up -d --build
# API:     http://localhost:8000
# Frontend http://localhost:8080
```

### 3) Local (no Docker)

```bash
# Requires Python 3.13+
# backend
pip install -r docker/backend/requirements.txt
# TODO: Update entrypoint once GLaDOS main module is implemented
# uvicorn GLaDOS.main:app --host 0.0.0.0 --port 8000 --reload

# frontend (in ./haro)
npm install
npm run dev   # http://localhost:3000
```


## Development Status

| Milestone | Status | Tests |
|-----------|--------|-------|
| M0: Test Infrastructure | ✅ Complete | 14 |
| M0.5: Project Restructure | ✅ Complete | +74 |
| M1: Foundation (DB/Events) | ✅ Complete | +124 |
| M2: API Live | ✅ Complete | +85 |
| M3: Veda Trading | ✅ Complete | +196 |
| M4: Greta Backtesting | ✅ Complete | +56 |
| M5: Marvin Core | ✅ Complete | +74 |
| M6: Live Trading | ✅ Complete | +101 |
| **M7: Haro Frontend** | ⏳ **Next** | ~50 |
| M8: Polish & E2E | ⏳ Pending | ~40 |

**Current**: 808 tests passing · Python 3.13 · pytest 9.x · FastAPI · SQLAlchemy 2.x

### Recent Changes (2026-02-04)

- ✅ **M6 Complete**: Live trading system with plugin adapter architecture (808 total tests)
- ✅ PluginAdapterLoader with AST-based discovery (40 tests)
- ✅ AlpacaAdapter connection management with connect/disconnect/is_connected (23 tests)
- ✅ VedaService wired to order routes for live order creation (13 tests)
- ✅ Live order flow with persistence and event emission (15 tests)
- ✅ RealtimeClock integration for live/paper runs (10 tests)
- ✅ Comprehensive Veda trading documentation (`docs/architecture/veda.md`)

### Next: M7 Haro Frontend (~50 tests)

- React app scaffold with Vite + TypeScript
- Dashboard page (system status, active runs)
- Runs page (list + detail view)
- Orders page
- SSE client integration for real-time updates


## Endpoints (essentials)

* REST: `GET /healthz`, `GET/POST /runs`, `GET /orders`, `GET /candles`
* Realtime: `GET /events/stream` (SSE)  ·  Alternative: `/events/tail` (REST incremental)

