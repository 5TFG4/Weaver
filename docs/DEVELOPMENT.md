# Development Methodology

> **IMPORTANT**: This methodology applies to ALL development in this project.
> Every new milestone, feature, or module MUST follow this framework.

## 0. Development Environment

### Backend + Frontend (Recommended)

The dev environment uses a **hybrid container approach**:

```
┌─────────────────────────────────────────────────────────────┐
│  VS Code (Dev Container → backend_dev)                      │
│  - Edit Python (src/) + React (haro/) in one window         │
│  - Python 3.13 + Node.js 20 installed                       │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│ backend_dev     │◀─ API ───│ frontend_dev    │
│ Python/FastAPI  │          │ Node.js/Vite    │
│ :8000           │          │ :3000           │
└─────────────────┘          └─────────────────┘
```

### Starting the Environment

```bash
# 1. Open in VS Code with Dev Containers extension
# VS Code will prompt to "Reopen in Container"

# 2. Environment initialization is automatic:
#    - docker/init-env.sh runs as initializeCommand
#    - Creates docker/.env from docker/example.env
#    - Injects any secrets from Codespaces/GitHub environment

# 3. After container rebuild, verify environment
node --version   # Should show v20.x
npm --version    # Should show v10.x+

# Manual setup (if needed):
cp docker/example.env docker/.env
# Edit docker/.env with your API keys
```

### Port Mapping

| Service        | Container Port | Host Port | URL                   |
| -------------- | -------------- | --------- | --------------------- |
| Backend API    | 8000           | 8000      | http://localhost:8000 |
| Frontend Dev   | 5173           | 3000      | http://localhost:3000 |
| PostgreSQL     | 5432           | 5432      | -                     |
| Debug (Python) | 5678           | 5678      | -                     |

### Frontend Development

The frontend runs in a **separate container** (`frontend_dev`) with hot reload:

```bash
# Frontend starts automatically when docker-compose runs
# If you need to restart:
docker compose -f docker/docker-compose.dev.yml restart frontend_dev

# View frontend logs:
docker compose -f docker/docker-compose.dev.yml logs -f frontend_dev
```

**Note**: The `node_modules` folder is in a named Docker volume (`frontend_node_modules`)
to avoid sync issues with the host filesystem.

---

## 1. Design-Complete, Execute-MVP

This project follows a **Design-Complete, Execute-MVP** approach combined with **TDD**.

```
PHASE 1: COMPLETE DESIGN   →  "Think big, plan everything"
PHASE 2: MVP EXECUTION     →  "Start small, deliver incrementally"
PHASE 3: TDD IMPLEMENTATION →  "Test first, code second"
```

**Key Insight**: MVP is about **HOW** we implement, not **WHAT** we design.

| Traditional MVP                 | Our Approach                           |
| ------------------------------- | -------------------------------------- |
| Design only what MVP needs      | Design everything, implement MVP first |
| May miss edge cases until later | Edge cases considered upfront          |
| Frequent design changes         | Stable interfaces from day one         |
| Risk of technical debt          | Architecture-first, less rework        |

## 2. TDD Cycle

```
RED → GREEN → REFACTOR → (repeat)
```

1. Write a failing test based on FULL DESIGN specification
2. Write MINIMAL code to make the test pass
3. Refactor to improve code quality (tests must stay green)
4. Commit with descriptive message
5. Move to next test

## 3. Milestone Document Structure

Every milestone MUST be documented with this structure:

```
PART A: FULL DESIGN
├── A.1 All Endpoints / APIs / Commands
├── A.2 All Data Models / Schemas
├── A.3 All Service Interfaces
├── A.4 Error Handling Strategy
└── A.5 File Structure

PART B: MVP EXECUTION PLAN
├── B.1 MVP Overview (build vs defer)
├── B.2 TDD Test Specifications
├── B.3-N Individual MVPs
├── B.N Success Criteria
└── B.N+1 What Remains
```

## 4. Checklist for New Milestones

Before starting implementation:

- [ ] All endpoints/interfaces documented with request/response schemas
- [ ] All data models defined with all fields
- [ ] All service interfaces specified
- [ ] All error cases enumerated
- [ ] MVPs broken into vertical slices
- [ ] Each MVP has "what to build" and "what to defer"
- [ ] All test cases written against full design

## 5. Testing Strategy

### Test Pyramid

```
        /\
       /E2E\        Few, slow, high confidence
      /------\
     /Integration\  Some, medium speed
    /------------\
   /    Unit      \ Many, fast, isolated
  /________________\
```

### Test Categories

| Type        | Location             | Purpose                      |
| ----------- | -------------------- | ---------------------------- |
| Unit        | `tests/unit/`        | Isolated component testing   |
| Integration | `tests/integration/` | Cross-component with real DB |
| E2E         | `tests/e2e/`         | Full system via HTTP         |

### Test Doubles & Sideloadable Modules

We use **sideloadable modules** instead of inline mocks for better reusability:

| Module                | Location                            | Purpose                                  |
| --------------------- | ----------------------------------- | ---------------------------------------- |
| `MockExchangeAdapter` | `src/veda/adapters/mock_adapter.py` | Controllable exchange for backtest/tests |
| Test Strategies       | `tests/fixtures/strategies.py`      | Reusable test strategy implementations   |

**MockExchangeAdapter** (Production sideloadable):

- Used in backtest mode, no real API calls
- `set_mock_price(symbol, price)` - Control price data
- `set_reject_next_order(bool, reason)` - Simulate failures
- `reset()` - Clear state between tests

**Test Strategy Fixtures** (Test-only):

- `DummyStrategy` - No-op, returns configurable actions
- `RecordingStrategy` - Records all inputs for assertions
- `PredictableStrategy` - Returns pre-configured action sequences

**Why sideloadable instead of inline mocks?**

- ✅ Reusable across test files
- ✅ Single source of truth for mock behavior
- ✅ Better type safety (real classes, not MagicMock)
- ✅ MockExchangeAdapter also used in actual backtest mode

### Testing Tools

#### Backend (Python)

- **pytest** + pytest-asyncio
- **httpx** for async HTTP client testing
- **respx** for mocking external HTTP calls
- **pytest-cov** for coverage

#### Frontend (React/TypeScript)

- **Vitest** - Vite-native test runner
- **React Testing Library** - Component testing
- **MSW (Mock Service Worker)** - API mocking
- **@testing-library/user-event** - User interaction simulation
- **Playwright** (M8) - E2E testing

## 6. Code Standards

1. **Decimal Precision**: Use `Decimal` for all monetary values
2. **Timestamps**: All times in UTC
3. **Async**: All I/O operations are async
4. **Type Hints**: Required on all public functions
5. **Docstrings**: Required on all public classes/functions

## 7. Anti-Patterns to Avoid

| Don't                       | Do                                       |
| --------------------------- | ---------------------------------------- |
| Design only current MVP     | Design complete, implement incrementally |
| Skip tests to "save time"   | TDD always                               |
| Hardcode config values      | Use `src/config.py`                      |
| Use `print()` for debugging | Use `logging` module                     |
| Catch generic `Exception`   | Catch specific exceptions                |
| Store secrets in code       | Use environment variables                |

## 8. Documentation Structure

### File Purposes

| File                         | Contains                       | Max Lines |
| ---------------------------- | ------------------------------ | --------- |
| `ARCHITECTURE.md`            | System overview, quick links   | ~150      |
| `DEVELOPMENT.md`             | Methodology, standards         | ~150      |
| `AUDIT_FINDINGS.md`          | Issue tracking, progress       | No limit  |
| `architecture/roadmap.md`    | Status, milestones, checklists | ~150      |
| `architecture/*.md`          | Module-specific docs           | ~200 each |
| `archive/milestone-details/` | Full designs per milestone     | No limit  |

### Roadmap Rules

**roadmap.md contains ONLY**:

- Current state table
- Milestone list with status
- Phase timeline
- Architecture invariants
- Entry gate checklists

**roadmap.md does NOT contain**:

- Full design specs (→ `archive/milestone-details/mX-name.md`)
- Issue details (→ `AUDIT_FINDINGS.md`)
- Code examples longer than 5 lines
- Test specifications

### New Milestone Workflow

1. Create `docs/archive/milestone-details/mX-name.md` with full design
2. Add one-line entry to `roadmap.md` milestone table
3. Link to detail doc from roadmap
4. Update status as work progresses
5. After completion, design doc becomes reference archive
