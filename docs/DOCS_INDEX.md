# Weaver Documentation Index

> Last updated: 2026-02-26  
> Goal: keep **all existing information**, while making each document responsible for exactly one thing.
> **Current State**: M7 ✅ Closed · M8 ✅ Complete (Fixes & Improvements) · M9 ⏳ Planned (E2E) · 998 total tests

## 1) Entry Layer (Start Here)

| Document                           | Responsibility                          | Notes                             |
| ---------------------------------- | --------------------------------------- | --------------------------------- |
| [../README.md](../README.md)       | Project intro + quickstart + doc entry  | Keep brief, no deep design detail |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System boundary, invariants, module map | No milestone execution details    |

## 2) Specification Layer (Single Source of Truth)

| Document                                                 | Single Source For                                       | Out of Scope                    |
| -------------------------------------------------------- | ------------------------------------------------------- | ------------------------------- |
| [DEVELOPMENT.md](DEVELOPMENT.md)                         | Development workflow, TDD, contribution/doc rules       | Runtime status and milestones   |
| [architecture/api.md](architecture/api.md)               | REST/SSE contracts and frontend API integration model   | Milestone planning              |
| [architecture/events.md](architecture/events.md)         | Event envelope, types, delivery/offset semantics        | UI state management detail      |
| [architecture/clock.md](architecture/clock.md)           | Time model, realtime/backtest clock semantics           | API status                      |
| [architecture/greta.md](architecture/greta.md)           | Greta backtest runtime, simulated fills, per-run state  | Exchange adapter internals      |
| [architecture/marvin.md](architecture/marvin.md)         | Strategy plugin loading and execution model             | Transport-level SSE details     |
| [architecture/config.md](architecture/config.md)         | Credentials, config classes, config security rules      | Adapter internal implementation |
| [architecture/deployment.md](architecture/deployment.md) | Deployment topology and ops procedures                  | Product roadmap                 |
| [architecture/veda.md](architecture/veda.md)             | Veda internals (adapter interfaces, order flow, models) | Global config policy            |
| [architecture/walle.md](architecture/walle.md)           | Persistence schema, repositories, migration lifecycle   | Frontend state behavior         |

## 3) Execution Layer (Frequently Updated)

| Document                                                                                                 | Responsibility                                | Rule                                               |
| -------------------------------------------------------------------------------------------------------- | --------------------------------------------- | -------------------------------------------------- |
| [MILESTONE_PLAN.md](MILESTONE_PLAN.md)                                                                   | Current and upcoming milestone execution plan | This is the authoritative milestone status         |
| [archive/milestone-details/m8-fixes-improvements.md](archive/milestone-details/m8-fixes-improvements.md) | M8/M8-R detailed TDD/MVP execution plan       | Keep detailed tasks here, not in milestone summary |
| [DESIGN_AUDIT.md](DESIGN_AUDIT.md)                                                                       | Active quality gate and open findings         | Keep only current actionable findings              |
| [TEST_COVERAGE.md](TEST_COVERAGE.md)                                                                     | Current test coverage snapshot and gaps       | Avoid duplicating roadmap logic                    |

## 4) Governance & History

| Document                                                                       | Responsibility                               | Rule                                                 |
| ------------------------------------------------------------------------------ | -------------------------------------------- | ---------------------------------------------------- |
| [DESIGN_REVIEW_PLAN.md](DESIGN_REVIEW_PLAN.md)                                 | Review methodology/process                   | Keep framework stable, move active defects elsewhere |
| [M8_FINAL_PYRAMID_REVIEW.md](M8_FINAL_PYRAMID_REVIEW.md)                       | Final M8 layered full-scope audit snapshot   | Release-close audit artifact                         |
| [AUDIT_FINDINGS.md](AUDIT_FINDINGS.md)                                         | Historical audit record and root-cause trail | Keep as traceability log; not execution source       |
| [archive/ARCHITECTURE_BASELINE_FULL.md](archive/ARCHITECTURE_BASELINE_FULL.md) | Baseline historical architecture snapshot    | Read-only historical reference                       |
| [archive/roadmap-full-backup.md](archive/roadmap-full-backup.md)               | Full historical roadmap backup               | Read-only historical reference                       |

## 5) Ownership Rules (Non-Negotiable)

1. Milestone status appears in **one** place: [MILESTONE_PLAN.md](MILESTONE_PLAN.md).
2. Open quality findings appear in **one** place: [DESIGN_AUDIT.md](DESIGN_AUDIT.md).
3. Historical audit trail remains in [AUDIT_FINDINGS.md](AUDIT_FINDINGS.md) (do not delete).
4. Test counts are authoritative in [TEST_COVERAGE.md](TEST_COVERAGE.md), and should include snapshot date.
5. Other docs may link to these sources, but should not duplicate mutable status blocks.
