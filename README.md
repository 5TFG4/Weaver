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
| Current milestone design | [M5 Marvin (Complete)](docs/archive/milestone-details/m5-marvin.md) |
| Next milestone | M6: Live Trading |



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
| **M6: Live Trading** | ⏳ **Next** | ~65 |
| M7-M8 | ⏳ Pending | — |

**Current**: 705 tests passing · Python 3.13 · pytest 9.x · FastAPI · SQLAlchemy 2.x

### Recent Changes (2026-02-04)

- ✅ **M5 Complete**: Marvin strategy system with plugin architecture (705 total tests)
- ✅ EventLog subscription mechanism for pub/sub
- ✅ PluginStrategyLoader with auto-discovery (AST-based, no hardcoded imports)
- ✅ SMA crossover strategy with configurable indicators
- ✅ data.WindowReady flow for event-driven data fetching
- ✅ Test fixture consolidation (DummyStrategy, RecordingStrategy)

### Next: M6 Live Trading (~65 tests)

- PluginAdapterLoader (mirrors strategy pattern)
- AlpacaAdapter connect() with real clients
- VedaService wired to order routes
- Live order flow with persistence + events
- RealtimeClock for live runs


## Endpoints (essentials)

* REST: `GET /healthz`, `GET/POST /runs`, `GET /orders`, `GET /candles`
* Realtime: `GET /events/stream` (SSE)  ·  Alternative: `/events/tail` (REST incremental)

