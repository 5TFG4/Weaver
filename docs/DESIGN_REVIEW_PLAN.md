# Design Review Plan (Weaver)

> **Document Charter**  
> **Primary role**: review methodology and process governance.  
> **Authoritative for**: review rubric, segment flow, and review output protocol.  
> **Not authoritative for**: active defect backlog details (use `DESIGN_AUDIT.md`).

> **Purpose**: Provide a repeatable, context-resilient review process for validating Weaver’s architecture and implementation against the documented design.
>
> **Primary Goal**: The system can run reliably long-term on a local machine (ops-ready), while each milestone is delivered via MVP-style iterations.
>
> **How this doc is used**:
>
> - This is the “home base” for the review plan, progress, and outcomes.
> - After each review segment, we update **Findings by Layer**, **Action Queue**, and **Next Segment**.
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

## 6. Findings by Layer (Logical Structure)

### 6.1 Global status

- **Current confidence**: Architecture direction is correct, but implementation contracts are still unstable.
- **Scope covered so far**: Layers 0–4 fully reviewed; Layer 5 verification completed at contract/test level.
- **Release posture**: Not merge-gate ready for M8 execution until P0 contract and runtime wiring issues are closed.

### 6.2 Layer 0–1 (Mission, boundaries, invariants)

**Status: Satisfied (direction coherent)**

- Modulith + GLaDOS-only northbound boundary remains a good fit for local long-running reliability.
- Multi-run isolation (`run_id`) and per-run/per-singleton split are structurally sound.
- Main risk is not direction but drift: old and new execution paths coexist and reintroduce ambiguity.

### 6.3 Layer 2–3 (Contracts + runtime semantics)

**Status: Mostly / Not Satisfied (contract baseline locked in docs, runtime convergence pending)**

| Contract / runtime expectation              | Current implementation / source                                                | Drift / risk                                                  |
| ------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| Health endpoint contract is unambiguous     | Backend exposes `/healthz`; frontend client prepends `/api/v1`                 | `/api/v1/healthz` mismatch yields false-negative health state |
| Runs lifecycle contract includes start/stop | Service has `RunManager.start()`; routes expose only `POST /{id}/stop`         | Frontend `startRun()` fails by contract                       |
| SSE event naming is stable                  | Backend emits `run.Started`; frontend listens `run.started`                    | Case-sensitive SSE mismatch causes silent run update loss     |
| Thin-events policy is explicit and enforced | Docs describe thin `ui.*`; runtime broadcasts raw domain event names/payloads  | Public event contract is ambiguous                            |
| Resume semantics are operationalized        | Offsets primitives exist; app startup does not wire SSE replay/resume consumer | At-least-once intent not fully realized at boundary           |

### 6.4 Layer 4 (Module internals)

**Status: Mostly / Not Satisfied (module intent right, seams not fully closed)**

| Module     | Responsibility status                                     | Key seams verified                                                                  | Primary risks discovered                                                                              |
| ---------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Veda**   | ✅ Facade + persistence + event emission shape is correct | `VedaService` ↔ `OrderManager` ↔ `OrderRepository`                                  | `list_orders(run_id=None)` reads in-memory state, not durable global store                            |
| **Greta**  | ✅ Per-run simulator boundary is clear                    | Uses shared `BarRepository` + `EventLog`                                            | Runtime subscription focuses on `backtest.FetchWindow`; order-intent event path closure is incomplete |
| **Marvin** | ✅ Mode-agnostic runner design is correct                 | Emits `strategy.FetchWindow` / `strategy.PlaceRequest`; consumes `data.WindowReady` | Depends on router/downstream wiring; chain degrades when router not active                            |
| **WallE**  | ✅ Persistence role is structurally consistent            | `BarRecord`, `VedaOrder`, `OutboxEvent`, `ConsumerOffset` align                     | API boundary still contains mock read paths, weakening source-of-truth                                |

### 6.5 Layer 5 (Implementation & tests verification)

**Status: Not Satisfied (critical path has explicit gaps)**

| Verification item (P0/P1)                              | Implementation evidence                                                        | Test evidence                                                                                       | Result                                                      |
| ------------------------------------------------------ | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Run start route exists and is tested                   | `/runs/{id}/start` route missing in `routes/runs.py`                           | `tests/unit/glados/routes/test_runs.py` only covers create/get/list/stop                            | **FAIL** (proposal needs re-discussion)                     |
| Health contract aligned frontend/backend               | Backend route is `/healthz`; frontend API base is `/api/v1`                    | Backend tests assert `/healthz`; no frontend health API test file present                           | **FAIL** (plan confirmed)                                   |
| SSE run events casing consistent                       | Backend constants use `run.Started`; frontend hook listens `run.started`       | `tests/unit/events/test_types.py` + `haro/tests/unit/hooks/useSSE.test.tsx` encode divergent casing | **FAIL** (plan confirmed)                                   |
| DomainRouter active in runtime                         | `DomainRouter` implemented but not wired in app lifespan                       | `tests/unit/glados/test_domain_router.py` verifies router in isolation only                         | **FAIL** (needs deeper discussion)                          |
| Per-run cleanup guarantees complete                    | `StrategyRunner.cleanup()` exists; RunManager stop/completion does not call it | Tests assert clock/context behavior, not subscription cleanup invariants                            | **FAIL** (jointly discuss with run-start/dependency design) |
| EventLog DB real-time path wired with listener pool    | App constructs `PostgresEventLog(session_factory=...)` only                    | Integration tests verify append/read/offset stores; no app-level SSE real-time wiring proof         | **FAIL** (needs deeper discussion)                          |
| Orders read path uses durable source with write parity | POST/DELETE uses Veda; GET/list routes still use mock service                  | Route/unit coverage validates current split behavior, not parity guarantee                          | **FAIL** (needs deeper discussion)                          |
| no-DB publish/stream policy is finalized               | Degraded matrix documents non-durable behavior baseline                        | No explicit acceptance test for no-DB publish/stream policy decision                                | **OPEN** (needs deeper discussion)                          |
| Offset store durability primitives                     | `PostgresOffsetStore` and models implemented                                   | `tests/integration/test_offset_store.py` covers persistence/concurrency                             | **PASS (primitive level)**                                  |

**Layer 5 merge-gate recommendation**

- **Recommendation**: **Do not treat current state as M8 merge-gate ready**.
- **Reason**: P0 contract and runtime wiring failures are functional blockers, not polish issues.
- **Immediate focus**: close contract baseline doc decisions first, then apply tests-first fixes on routing/startup wiring.

### 6.6 Segment 5 closure (Contract baseline docs)

**Status: Completed (doc-only closure for contract baseline)**

| Segment 5 target               | Document update                                           | Result   |
| ------------------------------ | --------------------------------------------------------- | -------- |
| API/Event contract appendix    | `docs/architecture/api.md`, `docs/architecture/events.md` | **DONE** |
| Degraded/no-DB behavior matrix | `docs/architecture/deployment.md`                         | **DONE** |
| Veda doc sync (env + enum)     | `docs/architecture/veda.md`                               | **DONE** |

**Decisions locked in docs**

- Health canonical path is `/healthz` in current runtime contract.
- SSE event names are case-sensitive passthrough of backend domain event types.
- Public SSE stream currently exposes domain events (not `ui.*` projection).
- No-DB mode is explicitly documented as degraded/non-durable.

**Remaining risk after Segment 5**

- Runtime still diverges from target contract on run-start route (`POST /api/v1/runs/{id}/start`).
- Frontend/backend health base-path and run-event casing mismatch remain implementation-level blockers.
- Runtime wiring gaps (DomainRouter activation, RunManager dependency injection, EventLog real-time path completeness) remain P0 code work.

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

Each completed layer must produce a short packet (added to the Findings by Layer section) with:

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
- Segment 2 (done) completes Layers 2–3 explicitly (contracts + runtime semantics) with code/doc cross-check.
- Segment 3 (done) completes Layer 4 module-internal review (Veda/Greta/Marvin/WallE).
- Segment 4 (done) completes Layer 5 implementation/test verification (contract pass/fail + merge-gate assessment).
- Next: synthesize doc-contract baseline updates (`api.md`, `events.md`, degraded-mode policy) before code remediation.

**Plan adaptation expectation**: After we complete Layer 2 and Layer 3, we must update the Layer 4/5 checklists and Action Queue ordering using the “Layer Handoff Packet” outputs.

---

## 7. Action Queue (Prioritized)

> This is the working backlog generated by the review. Keep items small, testable, and MVP-shaped.

### P0 (Do first)

- [x] **Freeze contract baseline in docs (before code edits)**: add Contract Appendix to `docs/architecture/api.md` + `docs/architecture/events.md` (health path, run start route contract, SSE casing/namespace, payload/reconnect semantics).
- [x] **Define degraded/no-DB behavior explicitly**: add a short matrix for DB-on vs DB-off runtime guarantees (especially SSE/run lifecycle visibility).
- [ ] **Wire DomainRouter into runtime pipeline** (**discussion required**): make `strategy.* → backtest/live.*` routing active in app lifecycle and prove via integration tests.
- [ ] **Add per-run cleanup guarantees** (**discussion required; tied to run-start/dependency design**) : ensure run completion/stop executes runner/greta unsubscribe cleanup paths to prevent long-running subscription leaks.
- [ ] **Inject RunManager runtime dependencies** (**discussion required; tied to run-start/cleanup design**) : app startup must provide `StrategyLoader` and required backtest dependencies for `/runs/{id}/start` readiness.
- [ ] **Align Runs “start” contract** (**re-discussion required**) : add `POST /api/v1/runs/{id}/start` route calling `RunManager.start()` + tests; confirm frontend `startRun()` works end-to-end.
- [ ] **Make SSE truly real-time (DB mode)** (**discussion required**): wire an asyncpg pool into `PostgresEventLog` so LISTEN/NOTIFY actually runs; add at least one integration test proving SSE receives an appended event.
- [ ] **Unify Orders list/get source of truth** (**discussion required**): in DB mode + Veda enabled, list/get must reflect the same persisted orders created by Veda (no mock for read paths).

### P1

- [x] Sync `docs/architecture/veda.md` with current config/model reality (ALPACA env var names + `OrderStatus` values including `submitting/submitted`).
- [ ] Update `docs/architecture/roadmap.md` current state and test-count snapshot references to avoid stale planning signals.
- [ ] Define durable global order list semantics in `VedaService` (`run_id=None` behavior) and cover with restart-oriented integration tests.
- [ ] Decide whether “no DB” mode must still publish/stream events (**discussion required**); if yes, wire `InMemoryEventLog` into app lifespan and test it.

### P2

- [ ] Record and reconcile version drift in M7 design doc (React/Router versions) or update implementation notes.

---

## 8. How We Update This Document

After each segment:

1. Update **Findings by Layer** with the latest pass/fail and evidence deltas
2. Update **Action Queue** (move items between P0/P1/P2 as needed)
3. Record any **decisions** (especially doc-vs-code resolution)
4. Update **Next Focus** so the plan always reflects current logical dependency order

---

## 9. Next Focus (Planned)

**Issue-package discussion and option narrowing (doc-only)**

- Inputs: all items marked **discussion required** in Layer 5 findings and Action Queue
- Output: per-package decision record (chosen option + reasons + acceptance criteria), then update implementation-facing P0/P1 plan

### 9.1 Package A — Run lifecycle design (Issues 1 + 5 + 6)

**Problem description**

- `POST /api/v1/runs/{id}/start` contract is missing at route layer.
- Run lifecycle ownership is split: start/stop status changes exist, but cleanup and dependency readiness are not guaranteed as one atomic lifecycle design.
- Startup wiring does not yet guarantee `RunManager` has all dependencies required to actually execute start in all modes.

**Trigger conditions**

- Any frontend/operator action that starts a run.
- Any run stop/completion path (normal stop, error stop, repeated stop).
- App startup in environments where strategy/backtest dependencies are partially configured.

**Observed/expected frequency**

- **High** for start-route mismatch (user-facing primary flow).
- **Medium–High** for cleanup gaps in long-running use (accumulates over repeated runs).
- **Medium** for dependency-injection failures (environment/config dependent).

**Severity**

- **High / P0**: directly blocks run control and can cause lifecycle instability.

**Decision constraint**

- **A1 is excluded**: “minimal route patch first” is not accepted and should not be considered further.

**Solution options**

1. **Option A2 — Lifecycle-first cohesive fix**
   - Treat start route + DI readiness + cleanup guarantees as one change set.
   - **Pros**: root-cause closure; cleaner long-running behavior; fewer follow-up hotfixes.
   - **Cons**: larger change scope; more tests needed before merge.

2. **Option A3 — Guarded phased rollout**
   - Phase 1: start route + strict readiness checks/fail-fast errors.
   - Phase 2: full cleanup/DI unification.
   - **Pros**: balances delivery speed and safety; explicit transitional behavior.
   - **Cons**: temporary dual behavior must be documented and tested.

### 9.2 Package B — Runtime event wiring (Issues 4 + 7)

**Problem description**

- `DomainRouter` exists but is not activated in runtime lifecycle.
- DB-mode EventLog realtime path (LISTEN/NOTIFY listener wiring) is incomplete at app level.
- Result: architecture intent exists in code pieces, but runtime chain is not end-to-end guaranteed.

**Trigger conditions**

- Strategy emits `strategy.*` intents expecting domain routing.
- SSE subscribers rely on real-time propagation from appended outbox events.
- Service restart or reconnect scenarios where listener tasks must be re-established.

**Observed/expected frequency**

- **High** in strategy-driven runs (router path is core flow).
- **Medium–High** in DB-mode realtime UI usage.
- **Medium** for restart/recovery edge cases (but high operational impact when it happens).

**Severity**

- **High / P0**: breaks core event-driven control plane and realtime observability.

**Solution options**

1. **Option B1 — Direct app-lifespan wiring**
   - Explicitly wire router/listener tasks in startup/shutdown.
   - **Pros**: straightforward, explicit lifecycle ownership.
   - **Cons**: app factory complexity increases; careful teardown ordering needed.

2. **Option B2 — Dedicated orchestration component**
   - Introduce a single runtime orchestrator for subscriptions/listeners.
   - **Pros**: centralizes lifecycle logic; cleaner extensibility.
   - **Cons**: additional abstraction and initial refactor overhead.

3. **Option B3 — Partial wiring with feature flags**
   - Enable router/listener paths incrementally behind toggles.
   - **Pros**: safer rollout and easier rollback.
   - **Cons**: configuration complexity; risk of environment drift.

### 9.3 Package C — Data source-of-truth and degraded policy (Issues 8 + 9)

**Problem description**

- Orders write path uses Veda/persistence while read path still uses mock service.
- no-DB mode is documented as degraded, but publish/stream behavior is still a policy decision point.
- Result: data truth and degraded behavior are both not fully deterministic for operators.

**Trigger conditions**

- Any workflow that creates/cancels then immediately lists/gets orders.
- Any environment running without DB_URL but expecting event visibility.
- Regression checks comparing paper/live behavior with UI order history.

**Observed/expected frequency**

- **High** for read/write mismatch in trading workflows.
- **Medium** for no-DB policy ambiguity (depends on local/dev usage patterns).

**Severity**

- Issue 8: **High / P0** (business correctness and operator trust).
- Issue 9: **Medium / P1** (policy clarity and expected behavior in degraded mode).

**Solution options**

1. **Option C1 — Hard unify to durable source (DB mode), strict degraded semantics**
   - DB mode: reads always from durable Veda/WallE source.
   - no-DB mode: explicit non-durable/no-guarantee behavior.
   - **Pros**: clear correctness model; easiest to reason about.
   - **Cons**: reduced convenience in no-DB local demos.

2. **Option C2 — Transitional dual-read with priority rules**
   - Prefer durable source, fallback to mock during migration window.
   - **Pros**: smoother migration; fewer immediate breakages.
   - **Cons**: temporary complexity; risk of inconsistent edge cases.

3. **Option C3 — In-memory event/read model for no-DB parity**
   - Add explicit in-memory event log + order read model when DB absent.
   - **Pros**: better local parity without DB.
   - **Cons**: extra subsystem to maintain; can blur production guarantees.

### 9.4 Decision recording template (for each package)

**Package A (Issues 1 + 5 + 6)**

- **Chosen option**: **A2 — Lifecycle-first cohesive fix** (current preference)
- **Why chosen (top 2 reasons)**:
  1.  Avoids recurring lifecycle debt by solving route + DI + cleanup as one system problem.
  2.  Better fit for long-running reliability goal than phased temporary behavior.
- **Rejected options + reason**:
  - A1 rejected: explicitly excluded; too likely to create rework.
  - A3 not selected (for now): useful fallback, but introduces transitional dual behavior.
- **Acceptance criteria (must all pass)**:
  - Start route exists and is contract-tested.
  - RunManager startup dependencies are validated before run start.
  - Stop/completion/error paths execute deterministic cleanup and are test-covered.
- **Rollback/mitigation plan**:
  - If cohesive change cannot be stabilized in one cycle, temporarily pivot to A3 with explicit fail-fast and documented transition constraints.

**Package B (Issues 4 + 7)**

- **Chosen option**: **B2 — Dedicated orchestration component** (current preference)
- **Why chosen (top 2 reasons)**:
  1.  Centralizes runtime subscription/listener lifecycle and reduces hidden wiring drift.
  2.  Scales better as more event consumers are added.
- **Rejected options + reason**:
  - B1 not preferred: faster, but increases app factory wiring complexity over time.
  - B3 not preferred: adds config/flag complexity unless staged rollout is strictly required.
- **Acceptance criteria (must all pass)**:
  - Router path (`strategy.*` → `live/backtest.*`) is active in runtime and integration-tested.
  - DB-mode listener path is active and SSE receives appended event in integration test.
  - Startup/shutdown ordering is deterministic and leak-free.
- **Rollback/mitigation plan**:
  - If orchestration extraction proves too disruptive, fall back to B1 as an interim implementation with clear debt ticket and deprecation window.

**Package C (Issues 8 + 9)**

- **Chosen option**: **C1 — Hard unify to durable source (DB mode), strict degraded semantics** (confirmed)
- **Why chosen (top 2 reasons)**:
  1.  Establishes one authoritative order truth in DB mode, restoring correctness and operator trust.
  2.  Keeps no-DB semantics explicit as degraded/local mode rather than pseudo-production parity.
- **Rejected options + reason**:
  - C2 not preferred by default: acceptable only as time-boxed migration bridge due to dual-path complexity.
  - C3 not preferred: increases maintenance surface and can blur production guarantees.
- **Acceptance criteria (must all pass)**:
  - In DB mode, order read/write paths are unified to durable source behavior.
  - no-DB behavior is explicitly non-durable and documented in API/deployment semantics.
  - Integration coverage demonstrates write→read parity in DB mode.
- **Rollback/mitigation plan**:
  - If full C1 unification cannot be completed in one pass, use C2 only as a short, explicitly tracked transition state.
