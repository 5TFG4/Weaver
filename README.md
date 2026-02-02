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

* **[Architecture Overview](docs/ARCHITECTURE.md)** — Start here

| Detail Docs | |
|-------------|---|
| [Events](docs/architecture/events.md) | Event model, envelope, delivery |
| [API](docs/architecture/api.md) | REST, SSE, thin events |
| [Clock](docs/architecture/clock.md) | Realtime & backtest clocks |
| [Config](docs/architecture/config.md) | Credentials, security |
| [Deployment](docs/architecture/deployment.md) | Docker, env vars |
| [Roadmap](docs/architecture/roadmap.md) | Progress tracking |



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
| M3-M7 | ⏳ Pending | — |

**Current**: 274 tests passing · Python 3.13 · pytest 9.x · FastAPI · SQLAlchemy 2.x

### Recent Changes (2026-02-02)

- ✅ **M2 Complete**: GLaDOS API with REST endpoints and SSE streaming (274 total tests)
- ✅ REST endpoints: /healthz, /api/v1/runs, /api/v1/orders, /api/v1/candles
- ✅ SSE streaming: /api/v1/events/stream with SSEBroadcaster
- ✅ CORS middleware and OpenAPI docs (/docs, /redoc)
- ✅ RunManager with start/stop lifecycle
- ✅ Mock OrderService and MarketDataService for MVP


## Endpoints (essentials)

* REST: `GET /healthz`, `GET/POST /runs`, `GET /orders`, `GET /candles`
* Realtime: `GET /events/stream` (SSE)  ·  Alternative: `/events/tail` (REST incremental)

