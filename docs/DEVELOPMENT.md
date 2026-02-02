# Development Methodology

> **IMPORTANT**: This methodology applies to ALL development in this project.
> Every new milestone, feature, or module MUST follow this framework.

## 1. Design-Complete, Execute-MVP

This project follows a **Design-Complete, Execute-MVP** approach combined with **TDD**.

```
PHASE 1: COMPLETE DESIGN   →  "Think big, plan everything"
PHASE 2: MVP EXECUTION     →  "Start small, deliver incrementally"  
PHASE 3: TDD IMPLEMENTATION →  "Test first, code second"
```

**Key Insight**: MVP is about **HOW** we implement, not **WHAT** we design.

| Traditional MVP | Our Approach |
|-----------------|--------------|
| Design only what MVP needs | Design everything, implement MVP first |
| May miss edge cases until later | Edge cases considered upfront |
| Frequent design changes | Stable interfaces from day one |
| Risk of technical debt | Architecture-first, less rework |

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

| Type | Location | Purpose |
|------|----------|---------|
| Unit | `tests/unit/` | Isolated component testing |
| Integration | `tests/integration/` | Cross-component with real DB |
| E2E | `tests/e2e/` | Full system via HTTP |

### Testing Tools

- **pytest** + pytest-asyncio
- **httpx** for async HTTP client testing
- **respx** for mocking external HTTP calls
- **pytest-cov** for coverage

## 6. Code Standards

1. **Decimal Precision**: Use `Decimal` for all monetary values
2. **Timestamps**: All times in UTC
3. **Async**: All I/O operations are async
4. **Type Hints**: Required on all public functions
5. **Docstrings**: Required on all public classes/functions

## 7. Anti-Patterns to Avoid

| Don't | Do |
|-------|-----|
| Design only current MVP | Design complete, implement incrementally |
| Skip tests to "save time" | TDD always |
| Hardcode config values | Use `src/config.py` |
| Use `print()` for debugging | Use `logging` module |
| Catch generic `Exception` | Catch specific exceptions |
| Store secrets in code | Use environment variables |
