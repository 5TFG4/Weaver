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

* Full spec: **[Architecture Baseline](docs/ARCHITECTURE_BASELINE.md)**

  * Quick jump: [Repository Structure](docs/ARCHITECTURE_BASELINE.md#11-repository-structure)
  * Quick jump: [Deployment & Environment](docs/ARCHITECTURE_BASELINE.md#8-deployment--environment)



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
uvicorn glados.main:app --host 0.0.0.0 --port 8000 --reload

# frontend (in ./haro)
npm install
npm run dev   # http://localhost:3000
```


## Development Status

| Milestone | Status |
|-----------|--------|
| M0: Test Infrastructure | ✅ Complete (14 tests) |
| M1: Foundation | 🔄 Next |
| M2: API Live | ⏳ Pending |
| M3-M7 | ⏳ Pending |

**Environment**: Python 3.13 · pytest 9.x · FastAPI · SQLAlchemy 2.x


## Endpoints (essentials)

* REST: `GET /healthz`, `GET/POST /runs`, `GET /orders`, `GET /candles`
* Realtime: `GET /events/stream` (SSE)  ·  Alternative: `/events/tail` (REST incremental)

