"""
Strategy Runner

Runs strategy code in response to clock ticks.
Mode-agnostic: doesn't know if backtest or live.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from src.events.protocol import Envelope
from src.marvin.base_strategy import BaseStrategy, StrategyAction

if TYPE_CHECKING:
    from src.events.log import EventLog


class StrategyRunner:
    """
    Runs strategy code in response to clock ticks.
    
    Mode-agnostic: works identically for live and backtest runs.
    The runner translates strategy actions into events that are
    routed appropriately based on run mode.
    
    Attributes:
        run_id: Current run identifier (set during initialize)
        symbols: Trading symbols for this run
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        event_log: "EventLog",
    ) -> None:
        """
        Initialize StrategyRunner.
        
        Args:
            strategy: The strategy to run
            event_log: Event log for emitting events
        """
        self._strategy = strategy
        self._event_log = event_log
        self._run_id: str | None = None
        self._symbols: list[str] = []

    @property
    def run_id(self) -> str | None:
        """Current run identifier."""
        return self._run_id

    @property
    def symbols(self) -> list[str]:
        """Trading symbols for this run."""
        return self._symbols

    async def initialize(self, run_id: str, symbols: list[str]) -> None:
        """
        Initialize for a run.
        
        Args:
            run_id: Unique run identifier
            symbols: List of symbols to trade
        """
        self._run_id = run_id
        self._symbols = symbols
        await self._strategy.initialize(symbols)

    async def on_tick(self, tick) -> None:
        """
        Handle clock tick.
        
        Delegates to strategy and emits resulting events.
        
        Args:
            tick: Clock tick with timestamp
        """
        actions = await self._strategy.on_tick(tick)

        for action in actions:
            await self._emit_action(action)

    async def on_data_ready(self, envelope: Envelope) -> None:
        """
        Handle data.WindowReady event.
        
        Passes data to strategy and emits any resulting events.
        
        Args:
            envelope: Event envelope with data payload
        """
        actions = await self._strategy.on_data(envelope.payload)

        for action in actions:
            await self._emit_action(action)

    async def _emit_action(self, action: StrategyAction) -> None:
        """
        Emit event for a strategy action.
        
        Args:
            action: The strategy action to emit
        """
        if action.type == "fetch_window":
            await self._emit_fetch_window(action)
        elif action.type == "place_order":
            await self._emit_place_request(action)

    async def _emit_fetch_window(self, action: StrategyAction) -> None:
        """
        Emit strategy.FetchWindow event.
        
        Args:
            action: Fetch window action
        """
        envelope = Envelope(
            type="strategy.FetchWindow",
            payload={
                "symbol": action.symbol,
                "lookback": action.lookback,
            },
            run_id=self._run_id,
            producer="marvin.runner",
        )
        await self._event_log.append(envelope)

    async def _emit_place_request(self, action: StrategyAction) -> None:
        """
        Emit strategy.PlaceRequest event.
        
        Args:
            action: Place order action
            
        Note:
            Decimal values are serialized as strings to preserve precision.
            Consumers should use Decimal(str_value) to deserialize.
        """
        envelope = Envelope(
            type="strategy.PlaceRequest",
            payload={
                "symbol": action.symbol,
                "side": action.side,
                "qty": str(action.qty),
                "order_type": action.order_type,
                "limit_price": str(action.limit_price) if action.limit_price else None,
                "stop_price": str(action.stop_price) if action.stop_price else None,
            },
            run_id=self._run_id,
            producer="marvin.runner",
        )
        await self._event_log.append(envelope)
