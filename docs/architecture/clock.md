# Clock System (Self‑Clock)

> Part of [Architecture Documentation](../ARCHITECTURE.md)

**Critical Design Note**: Python's `asyncio.sleep()` is not precise. The clock system must handle both realtime trading (strict wall‑clock alignment) and backtesting (fast‑forward simulation).

## 1. Clock Abstraction

The clock system uses a **strategy pattern** with a common interface:

```python
class BaseClock(ABC):
    @abstractmethod
    async def start(self, run_id: str, timeframe: str) -> None:
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
```

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
```

* **Precision Target**: ±50ms of intended tick time.
* **Fallback**: If system clock drifts significantly, log warning and continue.

## 3. BacktestClock (Simulation)

Used for **backtesting** where simulation should run as fast as possible.

* **Fast‑Forward Mode**: No actual sleeping; ticks are emitted immediately.
* **Simulated Time**: Advances based on historical data range.
* **Backpressure Awareness**: Wait for strategy to finish processing before advancing.

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

* **Speed**: Limited only by strategy execution time and I/O.
* **Determinism**: Same inputs produce same tick sequence.

## 4. Clock Selection (GLaDOS Responsibility)

GLaDOS selects the appropriate clock based on run mode:

```python
def create_clock(run_config: RunConfig) -> BaseClock:
    if run_config.mode == "live":
        return RealtimeClock(timeframe=run_config.timeframe)
    elif run_config.mode == "backtest":
        return BacktestClock(
            start_time=run_config.backtest_start,
            end_time=run_config.backtest_end,
            timeframe=run_config.timeframe
        )
```

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

| Timeframe | Code | Bar Alignment |
|-----------|------|---------------|
| 1 minute  | `1m` | `:00` seconds |
| 5 minutes | `5m` | `:00`, `:05`, `:10`, ... |
| 15 minutes| `15m`| `:00`, `:15`, `:30`, `:45` |
| 1 hour    | `1h` | `:00:00` |
| 1 day     | `1d` | `00:00:00 UTC` |

## 7. Files

```plaintext
src/glados/clock/
├── __init__.py
├── base.py           # BaseClock ABC, ClockTick dataclass
├── realtime.py       # RealtimeClock implementation
├── backtest.py       # BacktestClock implementation
└── utils.py          # Bar alignment calculations (17 tests)
```
