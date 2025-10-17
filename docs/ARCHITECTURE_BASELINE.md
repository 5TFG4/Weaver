# Weaver — Architecture Baseline



## 1. Document Goals & Scope

* **Goals**: Fix system **invariants** and boundaries; prevent implementation drift; provide a single shared vocabulary for collaboration, reviews, troubleshooting, and iteration.
* **Out of scope**: Library shootouts, full DDL/API samples, long code listings.



## 2. System Goals & Non‑Goals

* **Goals**:

  * A 24/7 automated trading system on a local server, supporting **live trading and backtesting**, **multi‑strategy concurrency**, **web UI**, and **containerized deployment**.
  * Integrate Alpaca first; keep the door open for more exchanges.
* **Non‑Goals (MVP)**:

  * Microservice split, distributed queues, or complex workflow engines.
  * Exactly‑once stream processing.
  * External multi‑tenant or complex auth systems.



## 3. Architecture Overview

### 3.1 Shape & Boundaries

* **Modulith**: A single backend process (Python) hosting domain packages: `GLaDOS / Events / Veda / Greta / Marvin / WallE`. **Only GLaDOS** exposes northbound APIs.
* **Frontend–Backend split**: Haro (React) runs as an independent container, talking to the backend via APIs.

### 3.2 External Interfaces

* **REST**: synchronous query & control.
* **Realtime**: prefer **SSE (thin events)**; **REST Tail (incremental polling)** is also supported. Contracts are equivalent and interchangeable.

### 3.3 Internal Collaboration Model

* **Synchronous calls**: Critical paths are in‑process function calls (GLaDOS assembles and calls Veda/Greta/Marvin/WallE).
* **Event‑driven**: For broadcast, decoupling, notifications, and replay. Implemented as **EventLog (Postgres Outbox + LISTEN/NOTIFY)**:

  * Business write and event append happen in the **same transaction** (`outbox`).
  * After commit, `NOTIFY` wakes subscribers.
  * Consumers persist progress in `consumer_offsets`. Delivery is **at‑least‑once**.
* **Strategy‑led**: Strategies express intent via events (fetch/order). GLaDOS performs **domain routing** (`strategy.* → live|backtest.*`).

### 3.4 Global Invariants

* **Time**: DB stores **UTC**; frontend renders in the user timezone.
* **Error model**: `{code, message, details, correlation_id}`.
* **Identity chain**: `id / corr_id / causation_id / trace_id`; events are immutable and replayable.



## 4. Modules — Responsibilities & Boundaries

> Defines what each module **does / does not** do. Library choices and low‑level details are out of scope.

### 4.1 GLaDOS (Control Plane & API)

* **Responsibilities**: Sole northbound API; run lifecycle; domain routing (`strategy.* → live|backtest.*`); self‑clock (align to bar timeframes); dependency wiring; publish thin events to the frontend.
* **I/O**: Inbound `strategy.* / run.*` (via REST or internal triggers); outbound `live|backtest.*` requests and `ui.*` thin events.
* **Constraints**: Does **not** write business tables directly (delegates to WallE); single publisher for events.

### 4.2 Veda (Live Data & Trading)

* **Responsibilities**: Handle `live.*` requests; call exchanges and cache for data, submit/query orders; emit `data.* / market.* / orders.*`.
* **Constraints**: Idempotent orders (`client_order_id`); global rate limits coordinated by GLaDOS; prefer cache hits.

### 4.3 Greta (Backtest Data & Simulation)

* **Responsibilities**: Handle `backtest.*` requests; produce historical windows; simulate fills/slippage/fees; emit `orders.*` and backtest stats.
* **Constraints**: Shares the same contracts as Veda; only the execution domain differs.

### 4.4 Marvin (Strategy Execution)

* **Responsibilities**: Maintain `run_id` context; tick by self‑clock; emit `strategy.FetchWindow/PlaceRequest`; consume `data.* / market.* / orders.*`; produce `strategy.DecisionMade`.
* **Constraints**: **Mode‑agnostic** (live/backtest); in‑flight backpressure keyed by `corr_id`.

### 4.5 WallE (Persistence Layer)

* **Responsibilities**: Centralized writes (`data.* / orders.* / strategy.DecisionMade`, etc.) and repository‑style reads for API.
* **Constraints**: Every table has `id, created_at(UTC), updated_at(UTC)`; single write path, auditable.

### 4.6 Haro (Web UI)

* **Responsibilities**: Show accounts/orders/runs/backtests; start/stop runs; consume SSE or REST Tail.
* **Constraints**: Subscribes **thin events only**; fetch details via REST.

### 4.7 Events (Protocol & Runtime)

* **Responsibilities**: Envelope/registry/validation; Outbox append & fan‑out; offsets management; retention/cleanup policy.
* **Implementation**: **EventLog (Postgres Outbox + LISTEN/NOTIFY)** — write business + event to `outbox` in one transaction; after commit, `NOTIFY` wakes consumers; progress stored in `consumer_offsets`; at‑least‑once, consumers deduplicate.
* **Constraints**: Thin events for UI; internal payload size policy in §5; protocol versioning supports parallel `*.v2`.



## 5. Event Model & Flows

### 5.1 Envelope (Stable Contract)

`{ id, kind:'evt'|'cmd', type, version, run_id, corr_id, causation_id, trace_id, ts, producer, headers, payload }`

### 5.2 Namespaces

`strategy.* / live.* / backtest.* / data.* / market.* / orders.* / run.* / ui.*`

### 5.3 Payload & Size Policy

* **Thin events** (to UI): keys + status only; fetch details via REST.
* **Internal events**: ≤ ~100KB inline; 100KB–2MB use `data.WindowChunk/Complete`; >2MB store **reference** only (`data_ref`).

### 5.4 Typical Flows

* **Fetch**: `strategy.FetchWindow → (GLaDOS route) → live|backtest.FetchWindow → data.WindowReady/Chunk/Complete`.
* **Orders**: `orders.PlaceRequest → orders.Ack/Placed/Filled/Rejected`.
* **Run**: `run.Started/StopRequested/Heartbeat`; `clock.Tick`.

### 5.5 Delivery & Idempotency

* Write `outbox` in‑transaction; `NOTIFY` after commit; resume via `consumer_offsets`; deduplicate by `id/corr_id`.



## 6. Data & Persistence

* **Business data (WallE)**: `orders / fills / candles / runs / backtests / strategy_results`, exposed via repositories.
* **EventLog**: `outbox` (fact log) and `consumer_offsets` (progress).
* **Retention & Cleanup**: time/partition based; TTL + audit retention; large payloads may use external storage (store references only).



## 7. External Interfaces

* **REST**: `/healthz`, `/runs` (list/start/stop), `/orders` query, `/candles` query.
* **Realtime**: `/events/stream` (SSE) or `/events/tail` (REST incremental).
* **Auth**: Local/private can run without auth; when exposed, use a **single API Key** (header), optionally with IP allow‑list.
* **Time semantics**: If no timezone specified in inputs, fall back to system default; responses are UTC or include timezone.



## 8. Deployment & Environment

### 8.1 Container Topology

* **Backend**: one multi‑stage Dockerfile (`dev`/`prod` targets).
* **Frontend**: `haro/Dockerfile` multi‑stage (`dev`: Node dev server; `prod`: Nginx static).
* **Compose**: `docker-compose.yml` (production‑like) + `docker-compose.dev.yml` (dev overrides).

### 8.2 Environment Variables & Secrets

* **Templates in repo**: `/.env.example` (prod template), `/.env.dev.example` (dev template).
* **Local files**: `.env / .env.dev` are copied from templates and **not committed** (`.gitignore`).
* **Build‑time args**: non‑secrets only (e.g., `VITE_API_BASE`).
* **Run‑time secrets**: DB/exchange keys injected by the deployment system; **never baked into image layers**.
* **CI build‑time private sources**: use **BuildKit Secrets** (ephemeral mounts, no layer leakage).

### 8.3 Migrations

* Use **Alembic** from day one; run `upgrade head` before release; keep migrations minimal and necessary.



## 9. Operations & Reliability

* **Backpressure**: throttle based on `consumer_offsets` lag thresholds.
* **Rate limiting**: live access coordinated by GLaDOS (DB token bucket/quotas).
* **Observability**: structured logs (include `run_id / corr_id`); optional metrics for lag/in‑flight/error rates.
* **Idempotency & Recovery**: event dedupe (`id/corr_id`); `client_order_id` on orders; consumers resume via offsets; outbox is replayable.



## 10. Versioning & Compatibility

* **Additive changes are backward‑compatible**; breaking changes use new names like `*.v2` and run in parallel for migration.
* **Pluggable implementation**: if LISTEN/NOTIFY is insufficient, swap `events/log.py` for Redis Streams/Kafka; protocol and business code remain unchanged.
* **Decomposition**: modules can be split into separate processes if needed, reusing the same protocol and offsets semantics.



## 11. Repository Structure

```plaintext
weaver/
├── README.md
├── LICENSE
├── .gitignore
├── .dockerignore
├── .editorconfig
├── pyproject.toml                     # tooling config only (no deps here)
├── .env.example                       # templates; .env/.env.dev are untracked
├── .env.dev.example                   # templates; .env/.env.dev are untracked
├── docker/
│   ├── backend/
│   │   ├── Dockerfile                 # multi-stage dev/prod
│   │   ├── requirements.txt           # runtime deps (single source of truth)
│   │   └── requirements.dev.txt       # dev deps (optional)
│   ├── docker-compose.yml             # production-like
│   └── docker-compose.dev.yml         # dev overrides
├── src/
│   ├── glados/
│   │   ├── app.py
│   │   ├── routes/
│   │   │   ├── api.py                 # /healthz, /runs, /orders, /candles
│   │   │   └── sse.py                 # /events/stream (or REST tail)
│   │   ├── domain_router.py           # route strategy.* → live|backtest.*
│   │   └── main.py                    # start EventPump/Clock/API
│   ├── events/
│   │   ├── protocol.py                # envelope/error model
│   │   ├── types.py                   # event name constants
│   │   ├── registry.py                # type→payload model registry/validation
│   │   ├── log.py                     # Outbox/LISTEN-NOTIFY/fan-out
│   │   ├── offsets.py                 # consumer_offsets management
│   │   └── retention.py               # TTL/cleanup/partitioning
│   ├── veda/
│   │   ├── handlers.py                # subscribe to live.* → produce data.* / market.*
│   │   ├── trading.py                 # orders.PlaceRequest → orders.*
│   │   └── alpaca_client.py
│   ├── greta/
│   │   └── handlers.py                # subscribe to backtest.* → data.* / orders.*
│   ├── marvin/
│   │   ├── handlers.py                # strategy intents/decisions
│   │   ├── timing.py                  # self-clock/backpressure
│   │   ├── base_strategy.py
│   │   └── strategies/
│   │       ├── sma_cross.py           # example strategy (optional placeholder)
│   │       └── README.md
│   ├── walle/
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── repos.py
│   │   └── handlers.py                # centralized writes
│   ├── config.py                      # providers/thresholds/concurrency
│   └── __init__.py
├── haro/
│   ├── Dockerfile                     # multi-stage: dev (dev server) / prod (Nginx static)
│   ├── package.json
│   ├── vite.config.ts                 # or webpack config
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts              # wraps REST + SSE (or REST tail)
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Runs.tsx
│       │   ├── Orders.tsx
│       │   └── Backtests.tsx
│       ├── components/
│       │   ├── EventFeed.tsx
│       │   └── Charts/
│       └── styles/
│           └── index.css
├── migrations/
│   ├── env.py
│   └── versions/
│       └── 0001_init.py
├── tests/
│   ├── unit/
│   │   ├── test_events_registry.py
│   │   ├── test_glados_router.py
│   │   ├── veda/
│   │   ├── greta/
│   │   ├── marvin/
│   │   └── walle/
│   ├── integration/
│   │   ├── test_fetch_window_flow.py
│   │   └── test_order_flow.py
│   └── e2e/
│       └── test_ui_basic.py
├── scripts/
│   ├── dev_up.sh                     # optional
│   └── seed_demo_data.py             # optional
├── .github/
│   └── workflows/
│       └── ci.yml                    # Lint/Test/Build
└── docs/
    └── ADRs/                         # Architecture Decision Records (optional)
```



## 12. Terms & Quick Reference

* **Modulith**: a single‑process architecture with multiple domain packages.
* **EventLog**: DB‑backed event log (Outbox + Offsets); `LISTEN/NOTIFY` is used only for wake‑ups.
* **Thin events**: keys/status only for realtime UI; details fetched via REST.
* **Domain routing**: translate `strategy.*` into `live.*` or `backtest.*` based on the execution domain.
