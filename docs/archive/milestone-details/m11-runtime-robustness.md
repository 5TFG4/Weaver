# M11: Runtime Robustness & UX Polish — Detailed Implementation Plan

> **Document Charter**
> **Primary role**: M11 milestone detailed implementation guide.
> **Authoritative for**: M11 task breakdown, file-level change specs, design decisions, test requirements, and execution order.
> **Not authoritative for**: milestone summary status (use `MILESTONE_PLAN.md`).

> **Status**: ✅ DECISIONS LOCKED — Ready for implementation
> **Prerequisite**: M10 ✅ (1089 tests: 946 backend + 104 frontend + 33 E2E + 6 Alpaca integration)
> **Estimated Effort**: 2–3 weeks
> **Branch**: `m11-runtime-robustness`
> **Key Inputs**: `CI_TEST_AUDIT.md` §7.7 (Backlog), `MILESTONE_PLAN.md` §7
> **Decisions Locked**: D-1(a), D-2(a), D-3(a), D-4(a), D-5(b) — 2026-03-23

---

## Table of Contents

1. [Current State — Verified Facts](#1-current-state--verified-facts)
2. [Goal & Non-Goals](#2-goal--non-goals)
3. [Undecided Design Questions](#3-undecided-design-questions)
4. [Execution Order & Dependencies](#4-execution-order--dependencies)
5. [M11-0: Dev Container Unification](#5-m11-0-dev-container-unification)
6. [M11-1: Backtest Async Race Fix (B-3)](#6-m11-1-backtest-async-race-fix-b-3)
7. [M11-2: Strategy Runtime Error Propagation (R-3)](#7-m11-2-strategy-runtime-error-propagation-r-3)
8. [M11-3: Concurrent Run Operation Safety (B-2)](#8-m11-3-concurrent-run-operation-safety-b-2)
9. [M11-4: CreateRunForm Error Feedback (F-2)](#9-m11-4-createrunform-error-feedback-f-2)
10. [M11-5: Cleanup & Exit Gate (B-10)](#10-m11-5-cleanup--exit-gate-b-10)
11. [Exit Gate](#11-exit-gate)
12. [Risk Assessment](#12-risk-assessment)

---

## 1. Current State — Verified Facts

All results measured on 2026-03-22; these are facts, not assumptions.

### 1.1 Test Totals (Post-M10 + CI Audit)

| Category           | Tests                 | Coverage |
| ------------------ | --------------------- | -------- |
| Backend unit       | 946                   | 89.73%   |
| Frontend unit      | 104                   | 94.8%    |
| E2E (Playwright)   | 33 (30 pass, 3 xfail) | -        |
| Alpaca integration | 6                     | -        |
| **Total**          | **1089**              | -        |

### 1.2 Known Runtime Bugs

| Bug                                     | Severity | Impact                                                    | Discovered         |
| --------------------------------------- | -------- | --------------------------------------------------------- | ------------------ |
| B-3: Backtest async race                | 🔴 P0    | Order events lost in every backtest. 3 E2E tests xfail.   | CI Audit Wave 2    |
| B-2: No concurrent run protection       | 🟡 P1    | Simultaneous start/stop → dict corruption, state teardown | Independent Review |
| R-3: Strategy runtime error propagation | 🟡 P1    | Unhandled exception in strategy → zombie run, no cleanup  | Independent Review |

### 1.3 Known UX Issues

| Issue                                     | Severity | Impact                                                                      |
| ----------------------------------------- | -------- | --------------------------------------------------------------------------- |
| F-2: CreateRunForm silent failures        | 🟡 P1    | API error → button resets, no feedback to user                              |
| B-10: Alpaca test skip placeholder bypass | 🟢 P2    | `ALPACA_PAPER_API_KEY=your_paper_api_key` bypasses skipif → 6 test failures |

### 1.4 Dev Environment Pain Points

| Issue                                            | Severity | Impact                                                       |
| ------------------------------------------------ | -------- | ------------------------------------------------------------ |
| B-8: No Docker CLI in dev container              | 🟡 P1    | Cannot run smoke/E2E tests from inside container             |
| B-9: check-local.sh requires bare host toolchain | 🟡 P1    | Developer needs full Python+Node+ruff+mypy installed locally |

### 1.5 Relevant Source Files (Verified Line Numbers)

| File                                         | Key Functions                                                      | Lines                           |
| -------------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |
| `src/glados/task_utils.py`                   | `spawn_tracked_task()`                                             | L8–L26                          |
| `src/glados/clock/backtest.py`               | `_tick_loop()`, `start()`, `stop()`                                | L110–L172, L72–L78, L68–L70     |
| `src/glados/services/run_manager.py`         | `_start_backtest()`, `_cleanup_run_context()`, `start()`, `stop()` | L264–L318, L166–L183            |
| `src/marvin/strategy_runner.py`              | `_on_window_ready()`, `on_data_ready()`, `cleanup()`               | L58–L66, L78–L87, L51–L56       |
| `src/greta/greta_service.py`                 | `_on_fetch_window()`, `_on_place_order()`, `cleanup()`             | L381–L397, L437–L445, L317–L327 |
| `src/glados/services/domain_router.py`       | `route()`                                                          | L35–L55                         |
| `haro/src/hooks/useRuns.ts`                  | `useCreateRun()`                                                   | L48–L57                         |
| `haro/src/components/runs/CreateRunForm.tsx` | Form submission                                                    | Full file                       |
| `haro/src/stores/notificationStore.ts`       | `addNotification()`                                                | Full file                       |

---

## 2. Goal & Non-Goals

### 2.1 Goals

1. **Fix the only known runtime bug** (B-3) — backtest order events must actually produce `orders.Placed` and `orders.Filled` events that survive to the outbox
2. **Add runtime safety guarantees** (B-2, R-3) — concurrent operations and strategy exceptions must not corrupt system state
3. **Close the UX gap** (F-2) — API failures must have visible user feedback
4. **Unify dev environment** (B-8, B-9) — single container can run full CI checks
5. **Remove test noise** (B-10) — no spurious failures in dev container

### 2.2 Non-Goals

1. **Multi-symbol backtests** (R-2) — requires Greta/WallE architectural changes beyond this scope
2. **Connection resilience** (R-1) — retry/circuit-breaker patterns require separate design work
3. **Pagination E2E tests** (E-3) — low-priority test coverage addition, not a bug fix
4. **Playwright in dev container** — E2E tests continue using the dedicated `test_runner` container
5. **Production deployment guide** — documentation-only, not runtime code

---

## 3. Design Decisions (All Locked)

> **All 5 decisions locked on 2026-03-23.** Implementation may proceed.

### D-1: Backtest Task Drain Strategy

**Context**: The B-3 bug occurs because `spawn_tracked_task()` creates fire-and-forget `asyncio.Task` objects with no mechanism to await their completion. When `_start_backtest()` exits and calls `_cleanup_run_context()`, in-flight tasks are abandoned.

**The trade-off**: We need a mechanism that guarantees all spawned tasks complete before cleanup, while preserving backtest performance (backtest clock must not become unnecessarily slow).

| Option                                             | Description                                                                                                                                          | Pros                                                                                  | Cons                                                                                                                                                                                                                                              |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **(a)** Task registry in RunContext                | Add `tasks: set[asyncio.Task]` to `RunContext`. `spawn_tracked_task()` registers tasks; cleanup `await asyncio.gather(*tasks)` before unsubscribing. | Clean, explicit ownership. Tasks belong to a run. Cleanup guarantees completion.      | Requires `RunContext` (or run_id) to be passed to `spawn_tracked_task`. Changes function signature.                                                                                                                                               |
| **(b)** Post-clock drain loop in `_start_backtest` | After `await clock.start(run.id)` returns, add `await asyncio.sleep(0)` in a loop (e.g., 3× or until pending count reaches 0).                       | Minimal code change. No API change to `spawn_tracked_task`.                           | Fragile — how many yields are enough? 3 hops today, could be more tomorrow. Heuristic, not a guarantee.                                                                                                                                           |
| **(c)** Backpressure via ack per event chain       | Use the existing `_use_backpressure` mechanism in BacktestClock. Each tick awaits full event chain completion before advancing.                      | Deterministic — each tick's work finishes before the next. Zero race by construction. | Requires `ack()` to be called only after the entire chain (3 hops) completes, not after the first handler. Complex to wire. May over-constrain future parallelism.                                                                                |
| **(d)** Convert fire-and-forget to awaited calls   | Replace `spawn_tracked_task(coro)` in callbacks with synchronous `await` (change callbacks from sync to async).                                      | No fire-and-forget = no race = no drain needed. Simplest mental model.                | EventLog `subscribe_filtered` callback is currently sync (`Callable[[Envelope], None]`). Changing to async callback requires modifying the EventLog dispatch contract — affects InMemoryEventLog, PostgresEventLog, and all existing subscribers. |

**Recommendation**: Option (a) — structural guarantee without timing heuristics or protocol changes.

**Decision**: 🔒 **LOCKED → (a) Task registry in RunContext** (2026-03-23)

**Rationale**: Option (a) provides a compile-time-visible ownership model: tasks belong to a `RunContext`, so cleanup can `await` them deterministically. Option (b) is heuristic (fragile). Option (c) requires deep changes to backpressure wiring for unclear future benefit. Option (d) requires changing the `EventLog` sync callback contract — too broad a blast radius for this fix.

### D-2: Concurrent Run Protection Scope

**Context**: `RunManager.start()` and `stop()` have no synchronization. Two concurrent `start()` calls for the same run could both pass the `if run.status != PENDING` check and create duplicate `RunContext` entries.

| Option                                        | Description                                                                                                                           | Pros                                              | Cons                                                                                                                                             |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **(a)** Per-run `asyncio.Lock`                | `_run_locks: dict[str, asyncio.Lock]`. Lock is acquired at the start of `start()`/`stop()` and released when the operation completes. | Granular — different runs don't block each other. | Dict of locks grows unbounded; need cleanup. Slightly more complex.                                                                              |
| **(b)** Single global `asyncio.Lock`          | One `_operation_lock` for all run operations.                                                                                         | Dead simple. Only one state mutation at a time.   | Serializes all run operations — two unrelated runs can't start concurrently. Acceptable for current single-user usage.                           |
| **(c)** Status CAS (compare-and-swap) pattern | Check-and-set status atomically. `start()` does `if run.status == PENDING: run.status = STARTING` in a single atomic operation.       | No locks. Idempotent.                             | Python dicts aren't truly atomic in async context. Still doesn't prevent two coroutines from both reading PENDING before either writes STARTING. |

**Recommendation**: Option (a) — correct granularity, well-understood async pattern.

**Decision**: 🔒 **LOCKED → (a) Per-run asyncio.Lock** (2026-03-23)

**Rationale**: Per-run locks avoid unnecessary serialization between independent runs. Lock cleanup is straightforward in `_cleanup_run_context`. Option (b) is simpler but serializes unrelated runs — an unnecessary limitation. Option (c) is unsafe in asyncio cooperative scheduling (any `await` between check-and-set introduces a race).

### D-3: Strategy Error Propagation Boundary

**Context**: If a strategy raises an exception during `on_tick()` or `on_data()`, the behavior depends on where the exception occurs in the chain. Currently:

- Exception in `runner.on_tick()` → propagates to `on_tick` callback → caught by BacktestClock tick loop → logged and skipped
- Exception in `runner.on_data_ready()` → inside `spawn_tracked_task` → logged by done callback → silently swallowed

| Option                                                     | Description                                                                                                                           | Pros                                                       | Cons                                                                                                                |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **(a)** Strategy errors → RunStatus.ERROR + cleanup        | Any unhandled strategy exception sets `run.status = ERROR`, emits `run.Error` event, and triggers cleanup. The run stops immediately. | Clear error semantics. User sees failure. Resources freed. | One bad tick kills the entire run. Some strategies may want to tolerate occasional errors (e.g., missing bar data). |
| **(b)** Strategy errors → logged + tick skipped + continue | Strategy errors are logged but the run continues on the next tick. After N consecutive errors, escalate to ERROR.                     | Resilient — transient errors don't kill the run.           | Threshold (N) is arbitrary. Risk of running in degraded state silently.                                             |
| **(c)** Configurable per-strategy error policy             | Strategy can declare `error_policy: "fail_fast"                                                                                       | "skip_tick"` in its metadata.                              | Flexible. Strategy author decides.                                                                                  | More complexity in StrategyMeta and runner. Over-engineering for current needs. |

**Recommendation**: Option (a) — a trading system must fail loudly, not run in degraded state.

**Decision**: 🔒 **LOCKED → (a) Fail fast → ERROR + cleanup** (2026-03-23)

**Rationale**: Silent continuation in a trading system risks executing with corrupted state. Option (a) is the only safe default. If a future strategy needs tolerance for transient errors (e.g., missing bar data), option (c) can be layered on top as an opt-in `error_policy` field — but that's M12+ scope, not M11.

### D-4: Dev Container Docker Socket Access

**Context**: To run `docker compose` commands from inside the dev container, the Docker socket must be accessible.

| Option                                                      | Description                                                                                                          | Pros                                                         | Cons                                                                                  |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| **(a)** Bind-mount `/var/run/docker.sock`                   | Add `- /var/run/docker.sock:/var/run/docker.sock` to `docker-compose.dev.yml`. Install Docker CLI in Dockerfile.dev. | Standard approach. Full Docker access from inside container. | Security: container has host Docker daemon access. Acceptable for dev-only container. |
| **(b)** Docker-in-Docker (DinD)                             | Run a separate Docker daemon inside the container.                                                                   | Full isolation from host Docker.                             | Complex setup. Performance overhead. Nested containers are harder to debug.           |
| **(c)** Docker socket proxy (Tecnativa/docker-socket-proxy) | Run a proxy container that restricts Docker API operations.                                                          | Fine-grained access control.                                 | Extra service to manage. Over-engineering for a dev container.                        |

**Recommendation**: Option (a) — industry standard for VS Code dev containers.

**Decision**: 🔒 **LOCKED → (a) Bind-mount Docker socket** (2026-03-23)

**Rationale**: VS Code Remote Containers official documentation recommends socket bind-mount for dev environments. DinD adds complexity with no benefit for a dev container. Socket proxy is production CI/CD tooling, overkill here. Security is not a concern — this container is explicitly development-only.

### D-5: check-local.sh Rewrite Strategy

**Context**: `check-local.sh` currently assumes bare-host toolchain (Python, Node, ruff, mypy). After B-8, we want it to work from inside the dev container.

| Option                                    | Description                                                                                                                                                                                             | Pros                                     | Cons                                                                             |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------- |
| **(a)** Single script, detect environment | `check-local.sh` detects if it's inside the container (e.g., check for `/.dockerenv`) and adjusts behavior. Inside: run directly with `DB_URL`. Outside: exec into container via `docker compose exec`. | One script for both environments.        | Conditional logic adds complexity. Two code paths to maintain.                   |
| **(b)** Two scripts: wrapper + inner      | `check-local.sh` (host wrapper) calls `docker compose exec backend_dev scripts/ci/check-all.sh`. `check-all.sh` (inner) runs all checks directly.                                                       | Clean separation. Each script is simple. | Two files to maintain. Developer must know which to run.                         |
| **(c)** Replace with Makefile             | `make check` runs inside container.                                                                                                                                                                     | Standard build tool. Tab-completion.     | Yet another tool in the chain. Not everyone is comfortable with Makefile syntax. |

**Recommendation**: Option (b) — clean separation, CI-reusable inner script.

**Decision**: 🔒 **LOCKED → (b) Two scripts: wrapper + inner** (2026-03-23)

**Rationale**: `check-all.sh` (inner) is a standalone CI script that runs identically inside the dev container and in GitHub Actions. `check-local.sh` (outer) becomes a one-line `docker compose exec` wrapper. Each script has a single responsibility. Option (a)'s environment detection is a maintenance burden. Option (c) introduces a Makefile for one use case — not justified.

---

## 4. Execution Order & Dependencies

```
M11-0: Dev Container Unification (B-8 + B-9)
  ├── D-4(a) socket bind-mount 🔒
  ├── D-5(b) two scripts 🔒
  ├── Dockerfile.dev: add Docker CLI
  ├── docker-compose.dev.yml: mount socket
  ├── scripts/ci/check-all.sh: container-internal CI
  └── scripts/ci/check-local.sh: thin wrapper
      │
      │ (M11-0 not a hard blocker for M11-1–M11-3,
      │  but provides a better debug environment)
      │
      ▼
M11-1: Backtest Async Race Fix (B-3)                    ← highest priority
  ├── D-1(a) task registry 🔒
  ├── task_utils.py: add task_set param
  ├── run_manager.py: RunContext.pending_tasks + drain before cleanup
  ├── greta_service.py: thread task_set into spawn calls
  ├── strategy_runner.py: thread task_set into spawn calls
  ├── Unit tests: verify task completion before cleanup
  └── E2E: 3 xfail tests should pass
      │
      ▼
M11-2: Strategy Error Propagation (R-3)                 ← same code path as M11-1
  ├── D-3(a) fail fast 🔒
  ├── backtest.py: exception → self._error + stop loop
  ├── run_manager.py: check clock._error → ERROR status + run.Error event
  ├── task_utils.py: propagate task exceptions via task_set drain results
  └── Unit tests: exception → ERROR status + cleanup
      │
      ▼
M11-3: Concurrent Run Safety (B-2)                      ← same code path as M11-1/2
  ├── D-2(a) per-run lock 🔒
  ├── run_manager.py: _run_locks dict + _get_run_lock()
  ├── start() / stop(): async with lock at entry
  └── Unit tests: concurrent start/stop → safe behavior
      │
      │ (M11-4 is frontend-only, parallel with M11-1–M11-3)
      │
M11-4: CreateRunForm Error Feedback (F-2)               ← independent, can start anytime
  ├── useRuns.ts: add onError to useCreateRun/useStartRun/useStopRun
  ├── useOrders.ts: add onError to useCancelOrder
  ├── Toast already exists (notificationStore)
  └── Frontend tests: error state + notification
      │
      ▼
M11-5: Cleanup & Exit Gate (B-10 + xfail removal + docs)
  ├── test_alpaca_paper.py: filter placeholder values in skipif
  ├── test_orders_lifecycle.py: remove xfail markers (after M11-1)
  └── Update MILESTONE_PLAN.md, roadmap.md, CI_TEST_AUDIT.md
```

---

## 5. M11-0: Dev Container Unification

> **Goal**: Developer can run all CI checks (lint, type-check, unit tests, integration tests) from inside the VS Code dev container with a single command.
> **Backlog Items**: B-8 (unified dev container), B-9 (local CI rewrite)
> **Estimated Tests**: 0 (infrastructure only)
> **Prerequisite Design Decisions**: D-4 (socket access), D-5 (script strategy)

### 5.1 Current State (Problem)

```
Developer Workflow Today:
┌─────────────────────────────────────────────┐
│ VS Code Dev Container (backend_dev)          │
│ ✅ Python 3.13 + ruff/mypy/pytest            │
│ ✅ Node 20 + npm (for IDE support)            │
│ ❌ No Docker CLI                              │
│ ❌ Cannot run: docker compose, smoke, E2E     │
│ ❌ check-local.sh fails inside container      │
└─────────────────────────────────────────────┘
         │
Developer must EXIT container and run from HOST:
  $ bash scripts/ci/check-local.sh     ← requires local Python/Node toolchain
  $ docker compose -f docker-compose.e2e.yml ...  ← requires host Docker
```

### 5.2 Target State

```
Developer Workflow After M11-0:
┌─────────────────────────────────────────────┐
│ VS Code Dev Container (backend_dev)          │
│ ✅ Python 3.13 + ruff/mypy/pytest            │
│ ✅ Node 20 + npm (for IDE + frontend tests)   │
│ ✅ Docker CLI (via socket mount)              │
│ ✅ bash scripts/ci/check-all.sh → full CI    │
│ ✅ DB_URL auto-set → integration tests run   │
└─────────────────────────────────────────────┘
```

### 5.3 Detailed Changes

#### 5.3.1 Dockerfile.dev — Add Docker CLI

**File**: `docker/backend/Dockerfile.dev`

**Current** (full file):

```dockerfile
FROM python:3.13-bookworm
WORKDIR /weaver

# Install Node.js 20 LTS (for VS Code TypeScript/ESLint extensions support)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && node --version && npm --version

# Install Python dev dependencies (includes production deps via -r requirements.txt)
COPY requirements.txt requirements.dev.txt /weaver/
RUN pip install --no-cache-dir -r requirements.dev.txt

COPY . /weaver/
CMD ["tail", "-f", "/dev/null"]
```

**After** (full file):

```dockerfile
FROM python:3.13-bookworm
WORKDIR /weaver

# Install Node.js 20 LTS (for VS Code TypeScript/ESLint extensions support)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && node --version && npm --version

# Install Docker CLI only (engine runs on host, accessed via socket mount)
# D-4(a): bind-mount /var/run/docker.sock in docker-compose.dev.yml
RUN apt-get update \
    && apt-get install -y ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
       | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) \
       signed-by=/etc/apt/keyrings/docker.gpg] \
       https://download.docker.com/linux/debian bookworm stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli docker-compose-plugin \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dev dependencies (includes production deps via -r requirements.txt)
COPY requirements.txt requirements.dev.txt /weaver/
RUN pip install --no-cache-dir -r requirements.dev.txt

COPY . /weaver/
CMD ["tail", "-f", "/dev/null"]
```

#### 5.3.2 docker-compose.dev.yml — Socket Mount

**File**: `docker/docker-compose.dev.yml`

**Change**: Add Docker socket volume to `backend_dev.volumes`:

```yaml
volumes:
  - ../:/weaver
  - /var/run/docker.sock:/var/run/docker.sock # Docker CLI access
  - /etc/timezone:/etc/timezone:ro
  - /etc/localtime:/etc/localtime:ro
```

**Security note**: This grants the dev container full access to the host Docker daemon. This is standard practice for dev containers and is documented by VS Code Remote Containers. The `.devcontainer/devcontainer.json` already specifies `"service": "backend_dev"`, meaning this is explicitly a development environment.

#### 5.3.3 scripts/ci/check-all.sh — Container-Internal CI (NEW)

**File**: `scripts/ci/check-all.sh` (NEW)

**Purpose**: Complete CI check script designed to run **inside** the dev container. Replaces the inner logic of the old `check-local.sh`. This single script is reusable both by developers (via `check-local.sh` wrapper) and by CI workflows directly.

**Full script**:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Designed to run INSIDE the dev container (backend_dev).
# All tools (Python, Node, ruff, mypy, Docker CLI) are pre-installed.
# DB_URL is set via docker-compose.dev.yml environment.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MODE="full"
VERBOSE=false
SMOKE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fast)  MODE="fast"; shift ;;
        --full)  MODE="full"; shift ;;
        --smoke) SMOKE=true; shift ;;
        -v)      VERBOSE=true; shift ;;
        *)       echo "Unknown option: $1"; exit 1 ;;
    esac
done

# run_step NAME CMD...
run_step() {
    local name="$1"; shift
    if $VERBOSE; then
        echo ""
        echo "--- $name ---"
        "$@"
        echo "  ✅ $name"
    else
        local tmp
        tmp=$(mktemp)
        printf "  %-35s" "$name"
        if "$@" > "$tmp" 2>&1; then
            echo "✅"
        else
            echo "❌"
            echo ""
            cat "$tmp"
            rm -f "$tmp"
            exit 1
        fi
        rm -f "$tmp"
    fi
}

echo "=========================================="
echo " CI Check (inside container)"
echo " Mode: $MODE | Smoke: $SMOKE"
echo "=========================================="
echo ""

# ── Backend ──────────────────────────────────
run_step "Backend: ruff check"    ruff check src/ tests/
run_step "Backend: ruff format"   ruff format --check src/ tests/
run_step "Backend: mypy"          mypy src/

if [[ "$MODE" == "fast" ]]; then
    run_step "Backend: pytest (unit)" \
        pytest -m "not container" --ignore=tests/e2e --ignore=tests/integration -q
else
    run_step "Backend: pytest (unit+integration)" \
        pytest -m "not container" --ignore=tests/e2e --cov=src --cov-report=term-missing -q

    if [[ -z "${DB_URL:-}" ]]; then
        echo "  ⚠  DB_URL not set — integration tests may have been skipped"
    fi
fi

# ── Frontend ─────────────────────────────────
echo ""
run_step "Frontend: eslint"       bash -c 'cd haro && npm run lint --silent'
run_step "Frontend: tsc"          bash -c 'cd haro && npx tsc -b --noEmit'
run_step "Frontend: vitest"       bash -c 'cd haro && npm run test --silent'
run_step "Frontend: build"        bash -c 'cd haro && npm run build --silent'

# ── Smoke (optional) ─────────────────────────
if $SMOKE; then
    echo ""
    run_step "Compose: smoke test" \
        docker compose -f docker/docker-compose.yml up -d --wait --wait-timeout 60
    run_step "Compose: health check" \
        bash -c 'curl -sf http://localhost:8000/api/v1/health | grep -q ok'
    run_step "Compose: teardown" \
        docker compose -f docker/docker-compose.yml down
fi

echo ""
echo "=========================================="
echo " All checks passed ✅"
echo "=========================================="
```

**Key differences from old `check-local.sh`**:

- `--fast` mode: skips integration tests and coverage (quick lint+type+unit cycle)
- `--full` mode (default): includes integration tests with coverage
- `--smoke` flag: runs compose smoke test (requires Docker socket from D-4)
- Always runs from project root via `ROOT_DIR` detection
- Reuses the `run_step` pattern from the existing script

#### 5.3.4 scripts/ci/check-local.sh — Thin Wrapper (D-5 = b)

**File**: `scripts/ci/check-local.sh` (REWRITTEN)

**Purpose**: Host-side wrapper that delegates to the dev container. For developers who run from the host terminal (not inside VS Code dev container).

**Full script**:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Host-side wrapper: delegates all CI checks to the dev container.
#
# Usage:
#   bash scripts/ci/check-local.sh           # full check
#   bash scripts/ci/check-local.sh --fast    # lint + type + unit only
#   bash scripts/ci/check-local.sh --smoke   # include compose smoke test
#   bash scripts/ci/check-local.sh -v        # verbose output
#
# Prerequisites: docker compose services must be running
#   docker compose -f docker/docker-compose.dev.yml up -d

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo " Local CI Check (via dev container)"
echo "=========================================="
echo ""

# Ensure dev services are running
if ! docker compose -f docker/docker-compose.dev.yml ps --status running backend_dev -q 2>/dev/null | grep -q .; then
    echo "  ⚠  backend_dev is not running. Starting dev services..."
    docker compose -f docker/docker-compose.dev.yml up -d --wait
fi

# Delegate to container-internal script, forwarding all arguments
docker compose -f docker/docker-compose.dev.yml exec -T backend_dev \
    bash scripts/ci/check-all.sh "$@"
```

**Backward compatibility note**: The old `check-local.sh` ran checks directly on the host. The new version delegates to the container. Developers who want the old bare-host behavior can run `bash scripts/ci/check-all.sh` directly (it works anywhere Python/Node/ruff/mypy are available).

### 5.4 What We Do NOT Change

1. **No Playwright browsers in dev container** — E2E tests use the dedicated `test_runner` container via `docker-compose.e2e.yml`. Installing Chromium/Firefox/WebKit would add ~500MB to the dev image for questionable benefit.
2. **No changes to `.devcontainer/devcontainer.json`** — It already points to `backend_dev` service. The Docker CLI and socket mount are compose-level changes.
3. **No changes to `frontend_dev` service** — Frontend dev server stays separate for hot reload isolation.
4. **No changes to production compose files** — `docker-compose.yml` and `docker-compose.e2e.yml` are unaffected.

### 5.5 Verification Checklist

```
- [ ] docker --version runs inside dev container
- [ ] docker compose version runs inside dev container
- [ ] docker compose -f docker/docker-compose.yml ps shows other services
- [ ] bash scripts/ci/check-all.sh --fast completes (lint + type + unit)
- [ ] bash scripts/ci/check-all.sh --full completes (includes integration)
- [ ] DB_URL is set and integration tests run (not skipped)
- [ ] Frontend checks pass inside container
```

---

## 6. M11-1: Backtest Async Race Fix (B-3)

> **Goal**: All `spawn_tracked_task` calls within a backtest run complete before `_cleanup_run_context()` unsubscribes event handlers.
> **Backlog Item**: B-3
> **Estimated Tests**: ~5 new
> **Design Decision**: D-1(a) Task registry in RunContext 🔒

### 6.1 Root Cause Analysis

The backtest execution chain involves 3 fire-and-forget task spawns:

```
Clock._tick_loop() [awaits] → on_tick(tick) callback:
  ├─ greta.advance_to(tick.ts) [awaited, completes]
  ├─ runner.on_tick(tick) [awaited, completions, emits strategy.FetchWindow]
  │
  │  EventLog.append(strategy.FetchWindow) triggers subscribers:
  │  └─ DomainRouter.route() → backtest.FetchWindow [awaited in append]
  │      └─ Greta._on_fetch_window [SYNC callback]
  │          └─ spawn_tracked_task #1: _handle_fetch_window() 🔥
  │              └─ event_log.append(data.WindowReady)
  │                  └─ StrategyRunner._on_window_ready [SYNC callback]
  │                      └─ spawn_tracked_task #2: on_data_ready() 🔥
  │                          └─ _emit_action(strategy.PlaceRequest)
  │                              └─ DomainRouter.route() → backtest.PlaceOrder
  │                                  └─ Greta._on_place_order [SYNC callback]
  │                                      └─ spawn_tracked_task #3: _handle_place_order() 🔥
  │                                          └─ place_order() → orders.Placed/Filled events
  │
  └─ [tick loop continues]
      └─ await asyncio.sleep(0) [ONLY 1 YIELD — tasks #1–#3 may not finish]
          └─ ... more ticks or loop exits ...

_start_backtest() [L318]:
  └─ _cleanup_run_context() — unsubscribes all handlers ⚠️
      Tasks #1–#3 still in-flight → orphaned, events lost
```

**Key observation**: The callbacks are **sync** (`Callable[[Envelope], None]`), so they cannot `await` the coroutine directly. They use `spawn_tracked_task()` to schedule async work, but nobody awaits those tasks.

### 6.2 Fix Strategy: D-1(a) Task Registry

The fix satisfies these invariants:

1. **Completeness**: Every spawned task finishes before cleanup
2. **Performance**: Backtest speed should not regress significantly
3. **Generality**: The solution works for N chained spawns, not just 3

### 6.3 Implementation Plan

#### 6.3.1 Task Registry in RunContext

**File**: `src/glados/services/run_manager.py`

**Before** (lines 97–113):

```python
from dataclasses import dataclass
# ...
@dataclass
class RunContext:
    """
    Per-run execution context.

    Holds all components that are instantiated per-run.
    For backtest: greta, runner, clock all set.
    For live/paper: greta is None (uses singleton VedaService).
    """

    greta: GretaService | None
    runner: StrategyRunner
    clock: BaseClock  # BacktestClock or RealtimeClock
```

**After**:

```python
import asyncio
from dataclasses import dataclass, field
# ...
@dataclass
class RunContext:
    """
    Per-run execution context.

    Holds all components that are instantiated per-run.
    For backtest: greta, runner, clock all set.
    For live/paper: greta is None (uses singleton VedaService).
    """

    greta: GretaService | None
    runner: StrategyRunner
    clock: BaseClock  # BacktestClock or RealtimeClock
    pending_tasks: set[asyncio.Task] = field(default_factory=set)
```

**Impact**: `pending_tasks` defaults to an empty set. All existing `RunContext(greta=..., runner=..., clock=...)` construction sites continue to work unchanged.

#### 6.3.2 Modified `spawn_tracked_task` Signature

**File**: `src/glados/task_utils.py`

**Before** (full file, 31 lines):

```python
def spawn_tracked_task(
    coro: Coroutine[Any, Any, Any],
    *,
    logger: logging.Logger,
    context: str,
) -> asyncio.Task[Any]:
    """Create an asyncio task and log unhandled exceptions with context."""
    task = asyncio.create_task(coro)

    def _on_done(done_task: asyncio.Task[Any]) -> None:
        try:
            done_task.result()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Background task failed: %s", context)

    task.add_done_callback(_on_done)
    return task
```

**After**:

```python
def spawn_tracked_task(
    coro: Coroutine[Any, Any, Any],
    *,
    logger: logging.Logger,
    context: str,
    task_set: set[asyncio.Task] | None = None,
) -> asyncio.Task[Any]:
    """Create an asyncio task and log unhandled exceptions with context.

    Args:
        coro: The coroutine to schedule.
        logger: Logger for exception reporting.
        context: Human-readable label for error messages.
        task_set: If provided, the task is added on creation and
                  removed via done-callback.  Used by RunContext to
                  track in-flight work for drain-before-cleanup.
    """
    task = asyncio.create_task(coro)

    def _on_done(done_task: asyncio.Task[Any]) -> None:
        if task_set is not None:
            task_set.discard(done_task)
        try:
            done_task.result()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Background task failed: %s", context)

    task.add_done_callback(_on_done)
    if task_set is not None:
        task_set.add(task)
    return task
```

**Backward compatibility**: `task_set=None` is the default. All 3 existing call sites (`_on_fetch_window`, `_on_window_ready`, `_on_place_order`) will be updated to pass `task_set`; no other callers of `spawn_tracked_task` exist in the codebase.

#### 6.3.3 Thread `task_set` Through Greta and StrategyRunner

Both `GretaService` and `StrategyRunner` need access to the task set for their spawned tasks.

**File**: `src/greta/greta_service.py`

**Change 1** — Add `_task_set` attribute in `__init__` (after `self._subscription_ids`):

```python
        self._subscription_ids: list[str] = []
        self._task_set: set[asyncio.Task] | None = None  # NEW: set by RunManager
```

**Change 2** — Add `task_set` parameter to `initialize()`:

```python
    async def initialize(
        self,
        symbols: list[str],
        timeframe: str,
        start: datetime,
        end: datetime,
        task_set: set[asyncio.Task] | None = None,  # NEW
    ) -> None:
        self._task_set = task_set
        # ... rest of initialization unchanged
```

**Change 3** — Pass `task_set` in both spawn sites:

```python
    def _on_fetch_window(self, envelope: Envelope) -> None:
        spawn_tracked_task(
            self._handle_fetch_window(envelope),
            logger=logger,
            context=f"greta.fetch_window run_id={self._run_id}",
            task_set=self._task_set,       # NEW
        )

    def _on_place_order(self, envelope: Envelope) -> None:
        spawn_tracked_task(
            self._handle_place_order(envelope),
            logger=logger,
            context=f"greta.place_order run_id={self._run_id}",
            task_set=self._task_set,       # NEW
        )
```

**File**: `src/marvin/strategy_runner.py`

**Change 1** — Add `_task_set` attribute in `__init__` (after `self._subscription_id`):

```python
        self._subscription_id: str | None = None
        self._task_set: set[asyncio.Task] | None = None  # NEW
```

**Change 2** — Add `task_set` parameter to `initialize()`:

```python
    async def initialize(self, run_id: str, symbols: list[str],
                         task_set: set[asyncio.Task] | None = None) -> None:
        self._task_set = task_set
        self._run_id = run_id
        self._symbols = symbols
        # ... rest unchanged
```

**Change 3** — Pass `task_set` in spawn site:

```python
    def _on_window_ready(self, envelope: Envelope) -> None:
        spawn_tracked_task(
            self.on_data_ready(envelope),
            logger=logger,
            context=f"marvin.window_ready run_id={self._run_id}",
            task_set=self._task_set,       # NEW
        )
```

#### 6.3.4 Wire `task_set` in `_start_backtest` and `_start_live`

**File**: `src/glados/services/run_manager.py`

**In `_start_backtest()` — pass `ctx.pending_tasks` to `initialize()` calls**:

```python
        # 3. Initialize components
        await greta.initialize(
            symbols=run.symbols,
            timeframe=run.timeframe,
            start=run.start_time,
            end=run.end_time,
            task_set=ctx.pending_tasks,    # NEW
        )
        await runner.initialize(
            run_id=run.id,
            symbols=run.symbols,
            task_set=ctx.pending_tasks,    # NEW
        )
```

**In `_start_live()` — same for runner** (no greta in live mode):

```python
        await runner.initialize(
            run_id=run.id,
            symbols=run.symbols,
            task_set=ctx.pending_tasks,    # NEW
        )
```

#### 6.3.5 Drain Before Cleanup

**File**: `src/glados/services/run_manager.py`

**Before** (`_cleanup_run_context`, lines ~199–213):

```python
    async def _cleanup_run_context(self, run_id: str) -> None:
        ctx = self._run_contexts.get(run_id)
        if ctx is None:
            return

        await ctx.clock.stop()
        await ctx.runner.cleanup()
        if ctx.greta is not None:
            await ctx.greta.cleanup()

        del self._run_contexts[run_id]
```

**After**:

```python
    async def _cleanup_run_context(self, run_id: str) -> None:
        """Cleanup per-run runtime resources.

        Cleanup contract (ordered for correctness):
        1. Stop clock (no more ticks generated)
        2. Drain pending tasks (spawned work completes before unsubscribe)
        3. Cleanup StrategyRunner subscriptions
        4. Cleanup GretaService subscriptions/state
        5. Remove context from manager
        """
        ctx = self._run_contexts.get(run_id)
        if ctx is None:
            return

        # 1. Stop clock — no more ticks
        await ctx.clock.stop()

        # 2. Drain in-flight tasks (NEW)
        if ctx.pending_tasks:
            await asyncio.gather(*ctx.pending_tasks, return_exceptions=True)

        # 3-4. Unsubscribe (safe now — all tasks complete)
        await ctx.runner.cleanup()
        if ctx.greta is not None:
            await ctx.greta.cleanup()

        del self._run_contexts[run_id]
```

**Why `return_exceptions=True`**: We don't want a failed task to prevent us from cleaning up the remaining resources. Failed tasks are already logged by the `_on_done` callback in `spawn_tracked_task`. The exceptions are collected here for M11-2 (error propagation) to inspect.

### 6.4 Test Plan

| #   | Test                                                | Type        | What It Verifies                                                |
| --- | --------------------------------------------------- | ----------- | --------------------------------------------------------------- |
| 1   | `test_spawn_tracked_task_registers_in_task_set`     | Unit        | Task appears in set, removed on completion                      |
| 2   | `test_spawn_tracked_task_removes_from_set_on_error` | Unit        | Failed task also removed from set                               |
| 3   | `test_cleanup_awaits_pending_tasks`                 | Unit        | `_cleanup_run_context` waits for tasks before unsubscribing     |
| 4   | `test_backtest_order_events_reach_outbox`           | Integration | Full backtest → `orders.Placed` + `orders.Filled` events in log |
| 5   | `test_backtest_multiple_ticks_all_tasks_complete`   | Integration | Multi-tick backtest with multiple order chains all complete     |

### 6.5 E2E Impact

After this fix, the 3 xfail tests in `tests/e2e/test_orders_lifecycle.py` should pass:

1. `test_backtest_generates_order_events`
2. `test_order_event_payloads_have_required_fields`
3. `test_backtest_strategy_signals_match_seed_data`

The `@pytest.mark.xfail` markers will be removed in M11-5.

---

## 7. M11-2: Strategy Runtime Error Propagation (R-3)

> **Goal**: A strategy that raises an exception during backtest execution results in a clean `RunStatus.ERROR` state with proper cleanup, not silent failure or zombie run.
> **Backlog Item**: R-3
> **Estimated Tests**: ~4 new
> **Design Decision**: D-3(a) Fail fast → ERROR + cleanup 🔒
> **Depends On**: M11-1 (task registry must exist for drain-exception inspection)

### 7.1 Current Behavior Analysis

Strategy code executes in two distinct contexts:

#### Context A: Synchronous tick path (inside `on_tick` callback)

```
BacktestClock._tick_loop()
  → on_tick(tick)                [callback registered in _start_backtest]
    → runner.on_tick(tick)       [awaited]
      → strategy.on_tick(tick)   [awaited — exception propagates HERE]
```

If `strategy.on_tick()` raises, the exception propagates to the `_tick_loop` `except Exception` handler at line ~140 in `backtest.py`:

```python
except Exception:
    logger.exception("Error in backtest clock tick loop, skipping tick")
    self._simulated_time += delta   # Skip to next tick
```

**Problem**: The exception is logged and the tick is skipped, but the run continues. No `run.Error` event. No status change. The run may produce incorrect results silently.

#### Context B: Asynchronous event path (inside spawned tasks)

```
spawn_tracked_task(_handle_fetch_window)
  → strategy.on_data(payload)   [inside awaited chain]
    → exception raised
      → caught by spawn_tracked_task's _on_done callback
        → logger.exception(...) — logged and swallowed
```

**Problem**: Strategy error in the async path is entirely swallowed. No status change, no cleanup, no user visibility.

### 7.2 Fix Strategy: D-3(a) Fail Fast

Any unhandled strategy exception → immediate run termination with `RunStatus.ERROR`. This is the only safe default for a trading system.

### 7.3 Implementation Plan

#### 7.3.1 Error Signal from BacktestClock

**File**: `src/glados/clock/backtest.py`

**Before** (inner `except` in `_tick_loop`, ~line 140):

```python
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Error in backtest clock tick loop, skipping tick")
                    self._simulated_time += delta
```

**After**:

```python
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception("Fatal error in backtest tick — stopping run")
                    self._error = exc
                    self._running = False
                    break
```

**Also add** `_error` attribute in `__init__` (after `self._use_backpressure = False`):

```python
        self._use_backpressure = False
        self._error: Exception | None = None  # NEW: stores fatal tick error
```

**Semantics**: The clock stops immediately on first unhandled exception. `_start_backtest` inspects `clock._error` to decide run status.

#### 7.3.2 Error-Aware `_start_backtest`

**File**: `src/glados/services/run_manager.py`

**Before** (in `_start_backtest`, after `await clock.start(run.id)`):

```python
            # 5. Run to completion (backtest is synchronous)
            await clock.start(run.id)
            run.status = RunStatus.COMPLETED
        except Exception:
            run.status = RunStatus.ERROR
            raise
```

**After**:

```python
            # 5. Run to completion (backtest is synchronous)
            await clock.start(run.id)

            # 6. Check for errors: clock tick error OR spawned task errors
            drain_errors: list[BaseException] = []
            if ctx.pending_tasks:
                results = await asyncio.gather(*ctx.pending_tasks, return_exceptions=True)
                drain_errors = [r for r in results if isinstance(r, BaseException)]

            clock_error = getattr(clock, '_error', None)
            if clock_error is not None or drain_errors:
                run.status = RunStatus.ERROR
                error_msg = str(clock_error) if clock_error else str(drain_errors[0])
                await self._emit_event(RunEvents.ERROR, run)
                logger.error("Backtest %s failed: %s", run.id, error_msg)
            else:
                run.status = RunStatus.COMPLETED
        except Exception:
            run.status = RunStatus.ERROR
            raise
```

**Note**: The drain now happens in `_start_backtest` before status assignment, rather than in `_cleanup_run_context`. This lets us inspect the drain results for errors. `_cleanup_run_context` still calls `gather` as a safety net, but the set should already be empty.

#### 7.3.3 Updated `_cleanup_run_context` (M11-1 + M11-2 combined)

Since M11-2 moves the primary drain into `_start_backtest`, `_cleanup_run_context` becomes a safety net:

```python
    async def _cleanup_run_context(self, run_id: str) -> None:
        ctx = self._run_contexts.get(run_id)
        if ctx is None:
            return

        await ctx.clock.stop()

        # Safety drain: tasks should already be empty if _start_backtest drained
        if ctx.pending_tasks:
            await asyncio.gather(*ctx.pending_tasks, return_exceptions=True)

        await ctx.runner.cleanup()
        if ctx.greta is not None:
            await ctx.greta.cleanup()

        del self._run_contexts[run_id]
```

### 7.4 Test Plan

| #   | Test                                    | Type | What It Verifies                                              |
| --- | --------------------------------------- | ---- | ------------------------------------------------------------- |
| 1   | `test_strategy_on_tick_error_stops_run` | Unit | Exception in `on_tick` → `run.status = ERROR`                 |
| 2   | `test_strategy_on_data_error_stops_run` | Unit | Exception in spawned `on_data_ready` → `run.status = ERROR`   |
| 3   | `test_error_run_emits_run_error_event`  | Unit | Error run emits `run.Error` event with error message          |
| 4   | `test_error_run_cleanup_completes`      | Unit | Error path still runs full cleanup (clock stop + unsubscribe) |

---

## 8. M11-3: Concurrent Run Operation Safety (B-2)

> **Goal**: Concurrent calls to `RunManager.start()` and `stop()` for the same or different runs do not corrupt internal state.
> **Backlog Item**: B-2
> **Estimated Tests**: ~5 new
> **Design Decision**: D-2(a) Per-run asyncio.Lock 🔒
> **Depends On**: M11-1 (same code, avoid conflicting changes)

### 8.1 Current Vulnerability Analysis

**`RunManager` internal state**:

```python
self._run_contexts: dict[str, RunContext] = {}   # No locking
self._runs: dict[str, Run] = {}                  # No locking
```

**Race scenario — double start**:

```
Coroutine A: start(run_id="abc") → reads run.status == PENDING
                                                           ← context switch
Coroutine B: start(run_id="abc") → reads run.status == PENDING
Coroutine A: creates RunContext, sets _run_contexts["abc"]
Coroutine B: creates another RunContext, OVERWRITES _run_contexts["abc"]
  → Coroutine A's RunContext is orphaned (clock running, no cleanup path)
  → Zombie clock + event handlers leak
```

**Race scenario — start/stop overlap**:

```
Coroutine A: start(run_id="abc") → begins _start_backtest, clock running
                                                           ← context switch
Coroutine B: stop(run_id="abc")  → calls _cleanup_run_context
  → Unsubscribes handlers while A still processing ticks
  → A continues with dead subscriptions → silent failures
```

### 8.2 Fix Strategy: D-2(a) Per-Run Lock

Each run gets its own `asyncio.Lock`. Operations on unrelated runs proceed concurrently; operations on the same run are serialized.

### 8.3 Implementation Plan

#### 8.3.1 Lock Registry

**File**: `src/glados/services/run_manager.py`

**Add to `__init__`** (after `self._run_contexts`):

```python
        self._run_contexts: dict[str, RunContext] = {}
        self._run_locks: dict[str, asyncio.Lock] = {}  # NEW: per-run locking
```

**Add helper method**:

```python
    def _get_run_lock(self, run_id: str) -> asyncio.Lock:
        """Get or create a per-run operation lock.

        Thread-safe in asyncio context because dict mutation between
        two synchronous Python statements has no yield point.
        """
        if run_id not in self._run_locks:
            self._run_locks[run_id] = asyncio.Lock()
        return self._run_locks[run_id]
```

#### 8.3.2 Lock Acquisition in `start()` and `stop()`

**`start()` — Before** (lines ~271–290):

```python
    async def start(self, run_id: str) -> Run:
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        if run.status != RunStatus.PENDING:
            raise RunNotStartableError(run_id, run.status.value)

        run.status = RunStatus.RUNNING
        # ...
```

**`start()` — After**:

```python
    async def start(self, run_id: str) -> Run:
        lock = self._get_run_lock(run_id)
        async with lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(run_id)

            if run.status != RunStatus.PENDING:
                raise RunNotStartableError(run_id, run.status.value)

            run.status = RunStatus.RUNNING
            # ... rest of method body indented under async with lock
```

**`stop()` — Before** (lines ~312–330):

```python
    async def stop(self, run_id: str) -> Run:
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        await self._cleanup_run_context(run_id)
        # ...
```

**`stop()` — After**:

```python
    async def stop(self, run_id: str) -> Run:
        lock = self._get_run_lock(run_id)
        async with lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(run_id)

            await self._cleanup_run_context(run_id)
            # ... rest of method body indented under async with lock
```

**Why the entire method body is inside the lock**: The status check and state mutation must be atomic. If only the status check were locked, the mutation could still race.

#### 8.3.3 Lock Cleanup

**In `_cleanup_run_context`** (add at end, before `del`):

```python
        del self._run_contexts[run_id]
        self._run_locks.pop(run_id, None)  # NEW: prevent lock dict growth
```

**Edge case**: The lock is being held by `start()`/`stop()` when `_cleanup_run_context` is called from within that locked block. Removing the lock from the dict while it's held is safe — the `asyncio.Lock` object itself stays alive until `async with` exits.

### 8.4 Test Plan

| #   | Test                                                | Type | What It Verifies                                                                |
| --- | --------------------------------------------------- | ---- | ------------------------------------------------------------------------------- |
| 1   | `test_concurrent_start_same_run_only_one_succeeds`  | Unit | Two `start()` calls for same run → only one creates RunContext                  |
| 2   | `test_concurrent_start_different_runs_both_succeed` | Unit | Two `start()` calls for different runs → both succeed (no global serialization) |
| 3   | `test_stop_during_start_waits_for_start`            | Unit | `stop()` blocks until `start()` completes, then stops cleanly                   |
| 4   | `test_double_stop_is_idempotent`                    | Unit | Two `stop()` calls for same run → no error, second is no-op                     |
| 5   | `test_run_lock_cleaned_up_after_run`                | Unit | Lock dict doesn't leak entries after run completes                              |

---

## 9. M11-4: CreateRunForm Error Feedback (F-2)

> **Goal**: When creating a run fails (API error), the user sees a clear error notification instead of silent button reset.
> **Backlog Item**: F-2
> **Estimated Tests**: ~4 new
> **Prerequisite Design Decisions**: None (independent frontend work)

### 9.1 Current Behavior

1. User fills form and clicks "Create Run"
2. `useCreateRun()` mutation fires `POST /api/v1/runs`
3. **On success**: Query cache invalidated, runs list refreshes. No success notification.
4. **On error**: `useMutation` resets `isPending` to `false`. Button returns to "Create Run". **No error message, no toast, no UI change.** User has no idea what happened.

### 9.2 Available Infrastructure

The notification system is already fully implemented and globally mounted:

| Component              | Location                               | Status         |
| ---------------------- | -------------------------------------- | -------------- |
| `Toast` component      | `haro/src/components/common/Toast.tsx` | ✅ Implemented |
| `useNotificationStore` | `haro/src/stores/notificationStore.ts` | ✅ Implemented |
| Toast mount point      | `haro/src/App.tsx`                     | ✅ Mounted     |
| Notification types     | `success`, `error`, `warning`, `info`  | ✅ Available   |
| Auto-dismiss           | 5 seconds                              | ✅ Working     |

### 9.3 Implementation Plan

#### 9.3.1 Add Error Callback to `useCreateRun`

**File**: `haro/src/hooks/useRuns.ts`

**Before** (lines 48–57):

```typescript
export function useCreateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RunCreate) => createRun(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
  });
}
```

**After** (centralized `onError` in hook definition — option i):

```typescript
import { useNotificationStore } from "../stores/notificationStore";

export function useCreateRun() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);
  return useMutation({
    mutationFn: (data: RunCreate) => createRun(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
    onError: (error: Error) => {
      addNotification({
        type: "error",
        message: error.message || "Failed to create run",
      });
    },
  });
}
```

#### 9.3.2 Apply Same Pattern to Other Mutation Hooks

Same `onError` → `addNotification` pattern applied to all mutation hooks:

**File**: `haro/src/hooks/useRuns.ts` — `useStartRun()`, `useStopRun()`:

```typescript
export function useStartRun() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);
  return useMutation({
    mutationFn: (runId: string) => startRun(runId),
    onSuccess: (data) => {
      queryClient.setQueryData(runKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
    onError: (error: Error) => {
      addNotification({
        type: "error",
        message: error.message || "Failed to start run",
      });
    },
  });
}

export function useStopRun() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);
  return useMutation({
    mutationFn: (runId: string) => stopRun(runId),
    onSuccess: (data) => {
      queryClient.setQueryData(runKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
    onError: (error: Error) => {
      addNotification({
        type: "error",
        message: error.message || "Failed to stop run",
      });
    },
  });
}
```

**File**: `haro/src/hooks/useOrders.ts` — `useCancelOrder()`:

```typescript
import { useNotificationStore } from "../stores/notificationStore";

export function useCancelOrder() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);
  return useMutation({
    mutationFn: (orderId: string) => cancelOrder(orderId),
    onSuccess: (_data, orderId) => {
      queryClient.invalidateQueries({ queryKey: orderKeys.detail(orderId) });
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
    onError: (error: Error) => {
      addNotification({
        type: "error",
        message: error.message || "Failed to cancel order",
      });
    },
  });
}
```

**Total changes**: 4 hooks across 2 files. Each adds `useNotificationStore` import and an `onError` callback.

### 9.4 Test Plan

| #   | Test                                                          | Type          | What It Verifies                                        |
| --- | ------------------------------------------------------------- | ------------- | ------------------------------------------------------- |
| 1   | `test_useCreateRun_shows_error_notification_on_api_failure`   | Frontend unit | API error → `addNotification({ type: "error" })` called |
| 2   | `test_useStartRun_shows_error_notification_on_api_failure`    | Frontend unit | Start failure → error notification                      |
| 3   | `test_useStopRun_shows_error_notification_on_api_failure`     | Frontend unit | Stop failure → error notification                       |
| 4   | `test_useCancelOrder_shows_error_notification_on_api_failure` | Frontend unit | Cancel failure → error notification                     |

---

## 10. M11-5: Cleanup & Exit Gate (B-10)

> **Goal**: Remove test noise, confirm all fixes work end-to-end, update documentation.
> **Backlog Items**: B-10 (Alpaca skip fix)
> **Estimated Tests**: 0 new (fix existing)

### 10.1 B-10: Alpaca Test Skip Placeholder Fix

**File**: `tests/integration/veda/test_alpaca_paper.py`

**Current skip condition** (line ~27):

```python
pytest.mark.skipif(
    not os.environ.get("ALPACA_PAPER_API_KEY")
    or not os.environ.get("ALPACA_PAPER_API_SECRET"),
    reason="ALPACA_PAPER_API_KEY and ALPACA_PAPER_API_SECRET must both be set",
)
```

**Problem**: When `.env` is created from `example.env`, the placeholder values `your_paper_api_key` / `your_paper_api_secret` are truthy strings, so the `skipif` condition evaluates to `False` and tests run — and fail because the credentials are bogus.

**Fix**: Add placeholder filtering:

```python
_PLACEHOLDER_VALUES = {"your_paper_api_key", "your_paper_api_secret", ""}

def _has_real_alpaca_creds() -> bool:
    key = os.environ.get("ALPACA_PAPER_API_KEY", "")
    secret = os.environ.get("ALPACA_PAPER_API_SECRET", "")
    return key not in _PLACEHOLDER_VALUES and secret not in _PLACEHOLDER_VALUES

pytest.mark.skipif(
    not _has_real_alpaca_creds(),
    reason="Real ALPACA_PAPER_API_KEY and ALPACA_PAPER_API_SECRET required",
)
```

### 10.2 Remove xfail Markers

**File**: `tests/e2e/test_orders_lifecycle.py`

After M11-1 is verified, remove `@pytest.mark.xfail(...)` from:

1. `test_backtest_generates_order_events`
2. `test_order_event_payloads_have_required_fields`
3. `test_backtest_strategy_signals_match_seed_data`

### 10.3 Documentation Updates

- `docs/MILESTONE_PLAN.md`: Update M11 status, test counts
- `docs/architecture/roadmap.md`: Add M11 to milestone table and phase timeline
- `docs/CI_TEST_AUDIT.md`: Move B-2, B-3, B-8–B-10, F-2, R-3 from "Backlog" to "Resolved (M11)"
- `docs/TEST_COVERAGE.md`: Update test totals

---

## 11. Exit Gate

### 11.1 Definition of Done

- [x] D-1 through D-5 design decisions all locked ✅ (2026-03-23)
- [x] Dev container has Docker CLI and socket mount (M11-0) ✅
- [x] `scripts/ci/check-all.sh` runs full CI inside container (M11-0) ✅
- [x] Backtest order events reach outbox — 3 xfail tests pass (M11-1) ✅
- [x] Strategy runtime errors produce `RunStatus.ERROR` + cleanup (M11-2) ✅
- [x] Concurrent `start()`/`stop()` calls are safe (M11-3) ✅
- [x] CreateRunForm shows error toast on API failure (M11-4) ✅
- [x] Alpaca tests skip correctly with placeholder credentials (M11-5) ✅
- [x] All xfail markers removed from E2E tests (M11-5) ✅
- [x] All CI workflows green ✅
- [x] Documentation updated with final test counts ✅

### 11.2 Test Targets

| Category           | Before M11            | Expected After M11        |
| ------------------ | --------------------- | ------------------------- |
| Backend unit       | 946                   | ~960 (+14 from M11-1/2/3) |
| Frontend unit      | 104                   | ~108 (+4 from M11-4)      |
| E2E                | 33 (30 pass, 3 xfail) | 33 (33 pass, 0 xfail)     |
| Alpaca integration | 6                     | 6 (no spurious failures)  |
| **Total**          | **1089**              | **~1107**                 |

---

## 12. Risk Assessment

| Risk                                                 | Probability | Impact | Mitigation                                                                    |
| ---------------------------------------------------- | ----------- | ------ | ----------------------------------------------------------------------------- |
| D-1 task registry adds complexity to all spawn sites | Medium      | Medium | Keep `task_set` optional; only pass it in run-scoped contexts                 |
| Docker socket mount breaks on non-Linux hosts        | Low         | Medium | Docker Desktop on Mac/Windows handles socket differently; document workaround |
| Locking in RunManager masks deeper state bugs        | Low         | Low    | Locks are a safety net; clean state machine is the real fix                   |
| `asyncio.gather` in drain hangs on stuck task        | Low         | High   | Add timeout: `asyncio.wait_for(gather(...), timeout=30)`                      |
| Frontend notification change breaks existing tests   | Low         | Low    | Existing tests don't mock notificationStore; new tests are additive           |

---

_Created: 2026-03-23_
_Decisions Locked: 2026-03-23 — D-1(a), D-2(a), D-3(a), D-4(a), D-5(b)_
_Status: 🟡 DECISIONS LOCKED — Ready for implementation_
