# Clock System (Self‑Clock)

> Part of [Architecture Documentation](../ARCHITECTURE.md)
>
> **Document Charter**  
> **Primary role**: runtime time semantics and clock component behavior.  
> **Authoritative for**: realtime/backtest clock behavior and tick cadence constraints.  
> **Not authoritative for**: API endpoints and milestone sequencing.

**Critical Design Note**: Python's `asyncio.sleep()` is not precise. The clock system must handle both realtime trading (strict wall‑clock alignment) and backtesting (fast‑forward simulation).

## 1. Clock Abstraction

The clock system uses a **strategy pattern** with a common interface:

```python
class BaseClock(ABC):
    def __init__(
        self,
        timeframe: str = "1m",
        callback_timeout: float = 30.0,  # Timeout for tick callbacks
    ) -> None:
        """Initialize with timeframe and callback timeout."""
        ...

    @abstractmethod
    async def start(self, run_id: str) -> None:
        """Start emitting clock.Tick events."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the clock."""
        pass

    @abstractmethod
    def current_time(self) -> datetime:
        """Return the current clock time (wall or simulated)."""
        pass

    def on_tick(self, callback: TickCallback) -> Callable[[], None]:
        """Register a callback for tick events. Returns unsubscribe function."""
        ...
```

### Callback Timeout Protection

Tick callbacks have a configurable timeout (default 30s) to prevent stuck backtests:

```python
async def _emit_tick(self, tick: ClockTick) -> None:
    for callback in self._callbacks:
        result = callback(tick)
        if asyncio.iscoroutine(result):
            await asyncio.wait_for(result, timeout=self._callback_timeout)
```

````

## 2. RealtimeClock (Live Trading)

Used for **live trading** where ticks must align to actual wall‑clock time.

* **Bar Alignment**: Ticks fire at the **start of each bar** (e.g., every minute at `:00` seconds).
* **Drift Compensation**: Calculate sleep duration dynamically to compensate for execution time.
* **Implementation Strategy**:
  1. Calculate `next_tick_time` based on timeframe (e.g., next minute boundary).
  2. Sleep until `next_tick_time - small_buffer` (e.g., 100ms before).
  3. Busy‑wait or precise sleep for the remaining time.
  4. Emit `clock.Tick` with `ts = next_tick_time` (not actual wall time).

```python
class RealtimeClock(BaseClock):
    """
    Emits clock.Tick aligned to wall-clock bar boundaries.

    Example for 1-minute bars:
      - 09:30:00.000 → Tick
      - 09:31:00.000 → Tick
      - 09:32:00.000 → Tick

    Handles drift by recalculating sleep duration each iteration.
    """
    async def _tick_loop(self):
        while self.running:
            next_tick = self._calculate_next_bar_start()
            await self._sleep_until(next_tick)
            await self._emit_tick(next_tick)
````

- **Precision Target**: ±50ms of intended tick time.
- **Fallback**: If system clock drifts significantly, log warning and continue.

## 3. BacktestClock (Simulation)

Used for **backtesting** where simulation should run as fast as possible.

- **Fast‑Forward Mode**: No actual sleeping; ticks are emitted immediately.
- **Simulated Time**: Advances based on historical data range.
- **Backpressure Awareness**: Wait for strategy to finish processing before advancing.

```python
class BacktestClock(BaseClock):
    """
    Emits clock.Tick as fast as possible for backtesting.

    Does NOT sleep. Advances simulated time immediately.
    Waits for strategy acknowledgment before next tick (backpressure).
    """
    def __init__(self, start_time: datetime, end_time: datetime, timeframe: str):
        self.simulated_time = start_time
        self.end_time = end_time
        self.timeframe = timeframe

    async def _tick_loop(self):
        while self.simulated_time <= self.end_time and self.running:
            await self._emit_tick(self.simulated_time)
            await self._wait_for_strategy_ack()  # backpressure
            self.simulated_time = self._advance_time()
```

- **Speed**: Limited only by strategy execution time and I/O.
- **Determinism**: Same inputs produce same tick sequence.

## 4. Clock Selection (GLaDOS Responsibility)

GLaDOS selects the appropriate clock using the factory function:

```python
from src.glados.clock import ClockConfig, create_clock

# Realtime trading (live or paper)
config = ClockConfig(timeframe="5m")
clock = create_clock(config)  # → RealtimeClock

# Backtesting
config = ClockConfig(
    timeframe="1h",
    backtest_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
    backtest_end=datetime(2025, 6, 30, tzinfo=timezone.utc),
)
clock = create_clock(config)  # → BacktestClock
```

**ClockConfig** is a frozen dataclass with validation:

- `timeframe`: Validated against supported values (1m, 5m, 15m, 30m, 1h, 4h, 1d)
- `backtest_start`/`backtest_end`: Must both be provided or neither (fail-fast validation)
- `is_backtest` property: Auto-detects mode based on whether times are set

## 5. clock.Tick Event

```python
@dataclass
class ClockTick:
    run_id: str
    ts: datetime          # Bar start time (not emission time)
    timeframe: str        # "1m", "5m", "1h", "1d"
    bar_index: int        # Sequential bar number within run
    is_backtest: bool     # Hint for logging/metrics (strategy should NOT use this for logic)
```

## 6. Timeframe Support

| Timeframe  | Code  | Bar Alignment                                        |
| ---------- | ----- | ---------------------------------------------------- |
| 1 minute   | `1m`  | `:00` seconds                                        |
| 5 minutes  | `5m`  | `:00`, `:05`, `:10`, ...                             |
| 15 minutes | `15m` | `:00`, `:15`, `:30`, `:45`                           |
| 30 minutes | `30m` | `:00`, `:30`                                         |
| 1 hour     | `1h`  | `:00:00`                                             |
| 4 hours    | `4h`  | `00:00`, `04:00`, `08:00`, `12:00`, `16:00`, `20:00` |
| 1 day      | `1d`  | `00:00:00 UTC`                                       |

## 7. Files

```plaintext
src/glados/clock/
├── __init__.py       # Public exports
├── base.py           # BaseClock ABC, ClockTick dataclass
├── factory.py        # ClockConfig + create_clock() factory
├── realtime.py       # RealtimeClock implementation
├── backtest.py       # BacktestClock implementation
└── utils.py          # Bar alignment calculations
```

**Test Coverage**: 93 tests, 93% coverage
