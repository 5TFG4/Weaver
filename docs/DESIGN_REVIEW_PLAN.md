# Design Review Plan (Weaver)

> **Purpose**: Provide a repeatable, context-resilient review process for validating Weaver’s architecture and implementation against the documented design.
>
> **Primary Goal**: The system can run reliably long-term on a local machine (ops-ready), while each milestone is delivered via MVP-style iterations.
>
> **How this doc is used**:
>
> - This is the “home base” for the review plan, progress, and outcomes.
> - After each review segment, we update **Progress & Results Log** and the **Action Queue**.
>
> **Scope**: Not just M7 (Haro). Covers the full system: GLaDOS, Events/SSE, Veda, Greta, Marvin, WallE, Config/Deployment, and cross-cutting invariants.

---

## 1. Review Principles

1. **Design-first validation**: Review starts from the design docs, then verifies code + tests.
2. **Long-running local reliability first**: Prefer fixes that improve durability (resource cleanup, reconnection, backpressure, error handling).
3. **MVP execution inside each milestone**: Implement vertically sliced increments with TDD (RED → GREEN → REFACTOR).
4. **Minimize drift**: If docs and code disagree, we either:
   - Update docs to match the chosen implementation, or
   - Change code to match the intended design.
     We always record the decision.
5. **Promote to Living Architecture**: If a subsystem (e.g., Greta, Marvin, WallE) relies solely on archived milestone docs, we extract the current design into a persistent `docs/architecture/` document to close the documentation gap.

---

## 2. Review Rubric (What “Good” Looks Like)

Each segment is scored as: **Satisfied / Mostly / Not Satisfied**, with a short justification.

### 2.1 Correctness & Safety

- API contracts match schemas and behavior.
- Event types are consistent and validated.
- Error model is stable and non-leaky (no ambiguous failures).
- Money/time semantics respected (Decimal, UTC).

### 2.2 Operability (Local Long-Running)

- Clean startup/shutdown (no orphan tasks, pools closed).
- Backpressure & bounded queues where needed.
- SSE/Event pipelines reconnect and degrade gracefully.
- Logs are actionable; failures are diagnosable.

### 2.3 Architecture Integrity

- No module singletons (services via DI / `app.state`).
- Multi-run isolation holds (events tagged with `run_id`, consumers filter).
- Clear boundaries: Haro consumes SSE + REST only; business logic stays backend.
- Plugin architecture works (strategies/adapters discoverable without hardcoded imports).

### 2.4 Testability

- TDD-friendly seams exist (interfaces, dependency injection).
- Unit/integration coverage exists for critical paths.
- Frontend uses MSW for API, avoids brittle network tests.

### 2.5 Consistency / Drift

- Roadmap, milestone design docs, and implementation are aligned.
- Version drift is recorded (e.g., React/Router versions) and not accidental.

---

## 3. Review Output Format (What We Produce Each Segment)

For each review segment, we publish a short report using this structure:

1. **Conclusion**: Satisfied / Mostly / Not Satisfied (3–6 bullets)
2. **Design→Code Alignment Table**:
   - Design expectation
   - Implementation location(s)
   - Test coverage location(s)
   - Drift / notes
3. **Risks (P0/P1/P2)**
   - **P0** = blocks long-running local reliability or next milestone execution
   - **P1** = serious but has workaround
   - **P2** = cleanup / polish
4. **Actionable Recommendations** (3–7 items)
   - Each includes: owner (us), acceptance criteria, and suggested tests
5. **Decisions / Open Questions** (max 1–3)

---

## 4. Review Segments (Order & Rationale)

We review in an order that minimizes rework and prioritizes reliability:

1. **Cross-cutting invariants & drift audit** (docs vs code vs tests)
2. **GLaDOS API + Dependency Injection** (boundaries, contract correctness)
3. **Events + SSE pipeline** (real-time behavior, backpressure, lifecycle)
4. **Veda live trading** (order lifecycle, persistence, event emission)
5. **Greta/Marvin backtest flow** (windowing, ticks, run isolation)
6. **WallE persistence/migrations** (schema correctness, transaction boundaries)
7. **Config + deployment (Docker/devcontainer)** (env vars, secrets, startup ergonomics)
8. **Haro frontend architecture** (API client, hooks, pages, SSE usage, tests)
9. **Synthesis: prioritized roadmap** (what to fix/build next)

---

## 5. Doc→Code Map (Index)

This is the index we use to avoid losing context across sessions.

### 5.1 Core planning docs

- `docs/ARCHITECTURE.md` — system overview and invariants
- `docs/architecture/roadmap.md` — current state + milestone status
- `docs/AUDIT_FINDINGS.md` — known issues and fix ordering
- `docs/DEVELOPMENT.md` — methodology (TDD + doc rules)

### 5.2 Module design docs

- `docs/architecture/api.md` → `src/glados/routes/*`, `src/glados/schemas.py`
- `docs/architecture/events.md` → `src/events/*`, `src/glados/sse_broadcaster.py`
- `docs/architecture/clock.md` → `src/glados/clock/*`
- `docs/architecture/config.md` → `src/config.py`, docker env files
- `docs/architecture/veda.md` → `src/veda/*`, `src/glados/routes/orders.py`
- `docs/architecture/deployment.md` → `docker/*`, `.devcontainer/*`

### 5.3 Milestone design docs (reference)

- M6: `docs/archive/milestone-details/m6-live-trading.md`
- M7: `docs/archive/milestone-details/m7-haro-frontend.md`

---

## 6. Progress & Results Log

> Append-only log. Each entry should be small and link to follow-up actions.

### 6.1 Current status

- **Review started**: 2026-02-06
- **Branch**: `haro_update`
- **Focus**: Long-running local reliability + MVP milestone execution

### 6.2 Log entries

#### 2026-02-06 — Initial triage (partial)

- Observed doc drift: `docs/architecture/roadmap.md` still marks Haro as not started while milestone plan indicates Haro progress.
- Observed API drift: frontend contains a `startRun()` call (`/runs/{id}/start`) while backend route list currently exposes only `/runs/{id}/stop`.
- Observed SSE risk: EventLog LISTEN/NOTIFY requires an asyncpg pool; if not wired, SSE may connect but not receive real-time events.

#### 2026-02-06 — Segment 0: Architecture direction & structure (design-doc review)

**Scope**: Validate the _big picture_ (direction, boundaries, invariants) using architecture docs only:
`docs/ARCHITECTURE.md`, `docs/architecture/events.md`, `docs/architecture/api.md`, `docs/architecture/clock.md`, `docs/architecture/veda.md`, `docs/architecture/deployment.md`, and the meta findings in `docs/AUDIT_FINDINGS.md`.

**Conclusion: Satisfied (direction is coherent), with 2–3 clarifying decisions to prevent future drift**

- **Modulith + strict northbound boundary (GLaDOS only)** is a good MVP shape for “local long-running reliability”: fewer moving parts, simpler deployment, easier debugging.
- **EventLog + Outbox + offsets** is the right durability primitive for a 24/7 system: replayable, crash-recoverable, and naturally supports fan-out consumers (SSE, persistence, runners).
- **Multi-run isolation via `run_id`** is a strong structural invariant that scales to parallel backtests + live/paper runs.
- **Thin events to UI** is a good UI contract choice to keep the SSE schema stable and payloads small.
- **Primary risk is not the design itself but ambiguity/parallelism**: the audit identifies “legacy vs modern architecture” coexisting, which will keep reintroducing drift unless we make a clear “one true path” decision and enforce it.

**Architecture integrity checks (design-level)**

| Invariant / direction             | Design intent                                              | Notes / risks                                                                                                                     |
| --------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| GLaDOS is the only northbound API | Haro talks REST+SSE only; domain modules don’t expose APIs | Needs enforcement to prevent “side doors” as features grow.                                                                       |
| EventLog is the durable backbone  | Outbox + LISTEN/NOTIFY + offsets                           | Great for local reliability; requires clear lifecycle + backpressure semantics (see Segment 3 later).                             |
| Multi-run is first-class          | per-run Greta/Marvin/Clock; singletons share infra         | Sound; requires every produced/consumed event to consistently carry `run_id`.                                                     |
| Thin events to UI                 | `ui.*` notifications + REST refetch                        | Docs currently show both raw domain events (`orders.*`, `run.*`) and example `ui.*` events; we need one explicit contract choice. |
| Dual credentials (live+paper)     | Parallel runs, not time-based switching                    | Sound; raises UI/ops need to clearly label run mode and safety defaults.                                                          |

**P0/P1 design decisions to lock down (before more implementation)**

- **P0 — SSE contract decision**: Do Haro clients receive raw domain events (`orders.*`, `run.*`) or only `ui.*` thin events?
  - If we choose `ui.*`: define the minimal stable payload keys per UI use-case and treat it as a versioned public contract.
  - If we choose raw domain events: Haro must treat them as semi-internal and we accept tighter coupling to backend event evolution.

- **P0 — “No DB mode” behavior**: When `DB_URL` is absent, do we expect _any_ event streaming / run lifecycle events to function, or is it a “degraded demo mode” with limited guarantees?
  - This matters because the design emphasizes “graceful degradation” but doesn’t explicitly define what the UI should expect without DB.

- **P1 — “One architecture” enforcement**: The audit’s root cause (“two parallel architectures”) implies we need an explicit migration/cleanup policy:
  - What is authoritative: the FastAPI app + app.state DI + modern services.
  - Everything else is deprecated/removed or moved under a clear `_deprecated/` boundary.

**Recommendations (design-only, no code yet)**

1. Write a 10–15 line “Contract Appendix” under the API + Events docs:
   - SSE event namespace choice (`ui.*` vs raw domain)
   - Minimal payload rules
   - Reconnection semantics expectations (Last-Event-ID support or not)

2. Write a 5–10 line “Degraded Mode” policy:
   - What works without DB (health? runs? SSE?)
   - What is explicitly unsupported without DB

3. Add a “Single Source of Truth” statement:
   - For orders: Veda + persistence is authoritative; mocks are test-only.
   - For runs: RunManager lifecycle is authoritative.

**Open questions (to answer in Segment 2/3)**

- Where is backpressure defined between EventLog → SSEBroadcaster → clients (bounded queues, drop policy, lag metrics)?
- What is the restart strategy: on process restart, should SSE consumers resume from offsets, or only stream live events?

---

## 10. Pyramid Review Structure (Top → Bottom)

> Goal: Review from **high-level architecture** down to **low-level implementation**, where each deeper layer expands into more concrete and testable checks.
>
> Principle: **Deeper layers may NOT contradict higher layers**. If a lower-layer finding conflicts, we either:
> (a) change implementation, or (b) revise the higher-layer document, recording the decision.

### Adaptive Planning Rule (Layer → Layer “Handoff”)

When we complete a layer, we **do not just record findings** — we also **update the plan for all deeper layers** so the review becomes guided rather than random.

This does **NOT** allow skipping checks in lower layers.
Instead, higher layers pass down what they learned so lower layers can:

- Focus first on the most uncertainty / risk-dense areas
- Use the correct contract decisions (so they don’t validate the wrong thing)
- Reduce wasted effort by marking “already-decided” items as _confirm-by-sampling_ rather than _re-deriving from scratch_

#### Required output of every layer review: “Layer Handoff Packet”

Each completed layer must produce a short packet (added to the Progress & Results Log) with:

1. **Decisions locked** (e.g., SSE contract choice, degraded/no-DB policy)
2. **Constraints** lower layers must respect (e.g., “GLaDOS-only northbound API”, “no module singletons”)
3. **Primary risks & unknowns** to prioritize in deeper layers
4. **Validation focus** for each deeper layer:
   - _Must-verify deeply_ (high risk / high uncertainty)
   - _Verify normally_ (baseline)
   - _Confirm by sampling_ (already clear at higher layer; still must not contradict)
5. **Artifacts to produce next** (which doc appendix / checklist / tests should be written next)

#### How deeper layers use the packet (non-optional)

- Lower layers must still cover their full checklist, but they may reorder work based on the packet.
- If deeper evidence contradicts an upstream decision, we escalate it as a **decision revisit** (not a silent divergence).
- If deeper layers discover new unknowns, those are bubbled up as _new constraints_ or _new contract clarifications_ for subsequent layers.

### Layer 0 — Mission & Non-Goals (smallest surface)

**Purpose**: Confirm we are building the right thing.

**Inputs**: `docs/ARCHITECTURE.md` (System Goals / Non-Goals).

**Checks**:

- 24/7 local reliability is the primary objective.
- MVP constraints are explicit (no microservices, no exactly-once, limited auth).
- Clear “what we will not do” to prevent scope creep.

**Output**: 3–6 bullets: “Direction OK / Direction change needed”.

### Layer 1 — Shape, Boundaries, and Invariants (architecture skeleton)

**Purpose**: Validate the system’s “shape” and where responsibilities live.

**Inputs**: `docs/ARCHITECTURE.md`, `docs/architecture/roadmap.md` (invariants).

**Checks**:

- Single northbound surface: GLaDOS is the only API boundary.
- Modulith boundaries are clear (Veda/Greta/Marvin/WallE/Events/Haro).
- Multi-run isolation rule is explicit (`run_id` everywhere).
- “No module singletons” is a hard invariant (services via DI).

**Output**: A short alignment table mapping each invariant to the intended owner module.

### Layer 2 — Contracts (REST + SSE + Event Envelope)

**Purpose**: Make interoperability stable and prevent drift.

**Inputs**: `docs/architecture/api.md`, `docs/architecture/events.md`.

**Checks**:

- REST routes are defined as a contract (methods, status codes, errors).
- SSE contract is explicitly chosen: `ui.*` thin events vs raw domain events.
- Envelope fields and identity chain are stable (`id/corr_id/causation_id/trace_id/run_id`).
- Versioning policy for contracts is stated (additive changes; `*.v2` for breaking).

**Output**: “Contract Appendix” (short, explicit) + a drift policy (how we decide doc vs code when mismatch occurs).

### Layer 3 — Runtime Semantics (long-running reliability)

**Purpose**: Validate that the design supports weeks-long uptime.

**Inputs**: `docs/architecture/events.md`, `docs/architecture/deployment.md`, `docs/architecture/clock.md`.

**Checks**:

- Lifecycle: startup/shutdown responsibilities are explicit (closing pools, stopping tasks).
- Backpressure policy exists (bounded queues, drop strategy, lag metrics).
- Reconnection strategy exists (SSE reconnect, EventLog resume semantics).
- Time semantics are explicit (UTC in DB, bar alignment, clock drift handling).

**Output**: A reliability checklist with “must-have for local long-running” items.

### Layer 4 — Module Internals (service responsibilities & seams)

**Purpose**: Validate each module’s internal structure supports the above layers.

**Inputs**: module docs: `docs/architecture/veda.md`, clock/events/etc.

**Checks**:

- Veda is the authoritative order lifecycle + persistence + event emission.
- Greta/Marvin separation: strategy logic stays mode-agnostic.
- WallE is the persistence layer (repos), not a service boundary.
- Test seams exist (interfaces, DI points, mockable adapters).

**Output**: For each module: 3–5 bullets (responsibilities, seams, risks).

### Layer 5 — Implementation & Tests (largest surface)

**Purpose**: Verify reality matches design and is regression-protected.

**Inputs**: code + tests.

**Checks**:

- Contract tests (REST/SSE) exist for P0 surfaces.
- Integration tests cover DB mode and degraded/no-DB mode expectations.
- Long-running hazards are tested (resource cleanup, reconnection, queue bounds).

**Output**: Concrete P0/P1/P2 fixes with tests-first acceptance criteria.

### How this maps to our current segment plan

- Segment 0 (done) covers Layers 0–1 at design level.
- Segment 1 (done) is an initial Layer 5 drift audit for the highest-risk contract points.
- Next: we should complete Layers 2–3 explicitly (contracts + runtime semantics) _in docs first_, then continue with deeper module reviews.

**Plan adaptation expectation**: After we complete Layer 2 and Layer 3, we must update the Layer 4/5 checklists and Action Queue ordering using the “Layer Handoff Packet” outputs.

#### 2026-02-06 — Segment 1: Cross-cutting invariants & drift audit (complete)

**Conclusion: Mostly / Not Satisfied (drift is impacting reliability + milestone execution)**

- **Runs lifecycle contract drifts**: backend implements create/get/list/stop, but not start; frontend calls `POST /runs/{id}/start`.
- **Orders source-of-truth is split**: create/cancel go through Veda, but list/get use a mock service (UI cannot reflect real orders reliably).
- **SSE “real-time” is not actually real-time when DB is enabled**: `PostgresEventLog` only starts LISTEN/NOTIFY when constructed with an asyncpg pool; app initializes it with only a session factory.
- **Docs drift exists and is untracked**: roadmap reports Haro “not started”; API docs omit `/runs/{id}/start` while frontend expects it.

**Design→Code Alignment Table**

| Design expectation                                   | Implementation location(s)                                                                                                     | Tests location(s)                         | Drift / notes                                                                                                                                                   |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Run lifecycle supports create → start → stop         | `src/glados/services/run_manager.py` has `start()`; routes: `src/glados/routes/runs.py`                                        | (missing for route)                       | Route for start is missing (`/runs/{id}/start`).                                                                                                                |
| Orders REST reflects real placed orders              | `src/glados/routes/orders.py`                                                                                                  | (existing tests cover Veda create/cancel) | GET/list use `MockOrderService`; create/cancel use `VedaService`.                                                                                               |
| SSE receives all events in real-time when DB enabled | `src/glados/app.py` subscribes broadcaster via `event_log.subscribe`; `src/events/log.py` requires `pool` to run listener task | (unclear / likely missing coverage)       | Listener task never starts without pool → no real-time delivery.                                                                                                |
| System degrades gracefully without DB_URL            | `src/glados/app.py` sets `event_log=None` without DB                                                                           | (unclear)                                 | SSEBroadcaster exists, but nothing publishes into it without an EventLog. If “no DB” mode is expected to still stream events, we should use `InMemoryEventLog`. |
| Planning docs reflect implementation status          | `docs/architecture/roadmap.md`, `docs/MILESTONE_PLAN.md`                                                                       | N/A                                       | Roadmap current state table is stale for Haro; milestone plan reflects M7-2 complete.                                                                           |

**Risks**

- **P0**: Runs “start” mismatch blocks Haro Runs page from working against backend.
- **P0**: SSE real-time likely non-functional with DB enabled; this undermines long-running local reliability and M7 SSE features.
- **P0**: Orders list/get won’t reflect Veda-created orders; UI correctness will be misleading during live/paper testing.
- **P1**: “No DB” mode may lose event streaming entirely unless we explicitly wire an in-memory EventLog.
- **P1**: Docs drift will keep reintroducing contract mistakes unless we treat it as work.

**Actionable Recommendations (tests-first)**

1. **Runs start endpoint**
   - Acceptance: backend exposes `POST /api/v1/runs/{id}/start` and returns the updated `RunResponse`.
   - Tests: unit/integration test for the route (404 unknown run; 409 or 400 if not startable; success transitions to RUNNING).
   - Frontend: keep `startRun()` as-is once backend is aligned.

2. **Make SSE real-time when DB enabled**
   - Acceptance: when DB is enabled, `PostgresEventLog` is constructed with an asyncpg pool, and the LISTEN/NOTIFY listener task is started on first subscribe.
   - Tests: add focused tests around `PostgresEventLog.subscribe()` starting the listener when pool exists; add an integration test to confirm `append()` leads to SSE publish.

3. **Unify Orders list/get with real state**
   - Acceptance: if VedaService is configured, GET/list routes return orders from the same persisted source that Veda writes (WallE repository), or Veda provides read APIs for order state.
   - Tests: integration test places an order (paper), then `GET /orders` includes it; `GET /orders/{id}` returns it.

4. **Docs drift cleanup (small but high leverage)**
   - Acceptance: `docs/architecture/roadmap.md` current state reflects Haro M7-2 status; API docs explicitly document chosen run start behavior.

---

## 7. Action Queue (Prioritized)

> This is the working backlog generated by the review. Keep items small, testable, and MVP-shaped.

### P0 (Do first)

- [ ] **Align Runs “start” contract**: add `POST /api/v1/runs/{id}/start` route calling `RunManager.start()` + tests; confirm frontend `startRun()` works end-to-end.
- [ ] **Make SSE truly real-time (DB mode)**: wire an asyncpg pool into `PostgresEventLog` so LISTEN/NOTIFY actually runs; add at least one integration test proving SSE receives an appended event.
- [ ] **Unify Orders list/get source of truth**: in DB mode + Veda enabled, list/get must reflect the same persisted orders created by Veda (no mock for read paths).

### P1

- [ ] Update `docs/architecture/roadmap.md` current state table to reflect Haro status (M7-2 complete).
- [ ] Decide and document SSE event naming contract (raw domain event types vs `ui.*` “thin events”), then enforce consistently.
- [ ] Decide whether “no DB” mode must still publish/stream events; if yes, wire `InMemoryEventLog` into app lifespan and test it.

### P2

- [ ] Record and reconcile version drift in M7 design doc (React/Router versions) or update implementation notes.

---

## 8. How We Update This Document

After each segment:

1. Add one entry to **Progress & Results Log**
2. Update **Action Queue** (move items between P0/P1/P2 as needed)
3. Record any **decisions** (especially doc-vs-code resolution)
4. Update the **deeper-layer plan** using the segment’s “Layer Handoff Packet” (priorities, ordering, and confirmation depth)

---

## 9. Next Segment (Planned)

**Segment 1**: Cross-cutting invariants & drift audit

- Inputs: `docs/ARCHITECTURE.md`, `docs/architecture/roadmap.md`, `docs/AUDIT_FINDINGS.md`
- Output: top drift list + P0 blockers for long-running local reliability
