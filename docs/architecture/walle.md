# WallE (Persistence Layer)

> Part of [Architecture Documentation](../ARCHITECTURE.md)
>
> **Document Charter**  
> **Primary role**: database schema, repository boundaries, and migration strategy.  
> **Authoritative for**: persistence model and storage responsibilities.  
> **Not authoritative for**: API contracts (see `api.md`).

## 1. Responsibility & Boundary

WallE provides durable storage for runtime state, market data, orders/fills, and event-delivery plumbing.

Core responsibilities:

- SQLAlchemy model registration (`Base.metadata`)
- async engine/session lifecycle
- repository interfaces for domain modules
- Alembic migration lifecycle

## 2. Database Session Model

`src/walle/database.py` defines:

- global `Database` holder,
- lazy async engine/session factory creation,
- scoped async session context manager,
- startup init and graceful shutdown close.

`DatabaseConfig` controls URL, pool size/overflow, and SQL echo behavior.

## 3. Table Inventory

Main persisted tables:

- `outbox` — append-only event log for async consumers
- `consumer_offsets` — per-consumer last processed offset
- `bars` — immutable OHLCV history for backtests
- `veda_orders` — durable order state snapshots
- `runs` — run metadata/status for restart recovery
- `fills` — immutable execution audit trail

## 4. Repository Pattern

WallE repositories expose focused use-cases instead of leaking ORM concerns:

- `BarRepository` — upsert/read historical bars and coverage checks
- `RunRepository` — save/get/list persisted runs for recovery
- `FillRepository` — append/list-by-order fill audit records

Design rule:

- bars are shareable (immutable),
- runs/fills are run/order scoped,
- write operations commit per repository call.

## 5. Migration Strategy

Alembic migrations are incremental and additive. Current chain includes:

1. `20260130_0000_001_initial_initial_tables.py`
2. `20260202_1818_a7efb08f089a_add_veda_orders_table.py`
3. `20260203_1000_c3b4a5d6e7f8_add_bars_table.py`
4. `20260225_1000_d4e5f6a7b8c9_add_runs_and_fills_tables.py`

Operational policy:

- apply migrations before backend startup in DB mode,
- keep model definitions centralized in `src/walle/models.py`,
- avoid defining SQLAlchemy models in domain modules.

## 6. Degraded Mode Notes

When DB is disabled/unconfigured:

- durable repositories are unavailable,
- run/fill persistence and restart recovery are disabled,
- EventLog falls back to in-memory behavior (non-durable).

See deployment degraded-mode matrix in `docs/architecture/deployment.md`.

## 7. Key Files

- `src/walle/database.py`
- `src/walle/models.py`
- `src/walle/repositories/`
- `src/walle/migrations/versions/`

---

_Last updated: 2026-02-26 (M8-D)_
