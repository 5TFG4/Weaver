"""
Tests for DomainRouter

Unit tests for routing strategy events to domain-specific events.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.glados.services.domain_router import DomainRouter
from src.glados.services.run_manager import Run
from src.glados.schemas import RunMode, RunStatus
from src.events.protocol import Envelope


def make_envelope(
    type_: str,
    run_id: str = "run-123",
    payload: dict | None = None,
) -> Envelope:
    """Factory for test envelopes."""
    return Envelope(
        id="evt-456",
        type=type_,
        payload=payload or {},
        run_id=run_id,
        producer="test",
    )


class TestDomainRouterInit:
    """Tests for DomainRouter initialization."""

    def test_requires_event_log(self) -> None:
        """DomainRouter requires event_log at construction."""
        mock_event_log = MagicMock()
        mock_run_manager = MagicMock()

        router = DomainRouter(
            event_log=mock_event_log,
            run_manager=mock_run_manager,
        )

        assert router._event_log is mock_event_log

    def test_requires_run_manager(self) -> None:
        """DomainRouter requires run_manager at construction."""
        mock_event_log = MagicMock()
        mock_run_manager = MagicMock()

        router = DomainRouter(
            event_log=mock_event_log,
            run_manager=mock_run_manager,
        )

        assert router._run_manager is mock_run_manager


class TestDomainRouterRoute:
    """Tests for DomainRouter.route()."""

    @pytest_asyncio.fixture
    async def router(self) -> DomainRouter:
        """Create router with mocked dependencies."""
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        mock_run_manager = AsyncMock()
        mock_run_manager.get = AsyncMock(
            return_value=Run(
                id="run-123",
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                status=RunStatus.RUNNING,
                symbols=["BTC/USD"],
                timeframe="1m",
                config=None,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )

        return DomainRouter(
            event_log=mock_event_log,
            run_manager=mock_run_manager,
        )

    async def test_ignores_non_strategy_events(self, router: DomainRouter) -> None:
        """route() ignores events not starting with strategy."""
        event = make_envelope(type_="orders.Placed")

        await router.route(event)

        cast(AsyncMock, router._event_log).append.assert_not_called()

    async def test_ignores_unknown_run(self, router: DomainRouter) -> None:
        """route() ignores events with unknown run_id."""
        router._run_manager.get = AsyncMock(return_value=None)  # type: ignore[method-assign]
        event = make_envelope(type_="strategy.FetchWindow", run_id="unknown")

        await router.route(event)

        cast(AsyncMock, router._event_log).append.assert_not_called()

    async def test_routes_fetch_window_to_backtest(self, router: DomainRouter) -> None:
        """strategy.FetchWindow → backtest.FetchWindow for backtest runs."""
        event = make_envelope(
            type_="strategy.FetchWindow",
            payload={"symbol": "BTC/USD", "lookback": 10},
        )

        await router.route(event)

        event_log = cast(AsyncMock, router._event_log)
        event_log.append.assert_called_once()
        routed = event_log.append.call_args[0][0]
        assert routed.type == "backtest.FetchWindow"
        assert routed.run_id == "run-123"
        assert routed.payload == {"symbol": "BTC/USD", "lookback": 10}

    async def test_routes_place_request_to_backtest(self, router: DomainRouter) -> None:
        """strategy.PlaceRequest → backtest.PlaceOrder for backtest runs."""
        event = make_envelope(
            type_="strategy.PlaceRequest",
            payload={"symbol": "BTC/USD", "side": "buy", "qty": "1"},
        )

        await router.route(event)

        routed = cast(AsyncMock, router._event_log).append.call_args[0][0]
        assert routed.type == "backtest.PlaceOrder"

    async def test_routes_to_live_for_paper_mode(self, router: DomainRouter) -> None:
        """strategy.* → live.* for paper trading runs."""
        router._run_manager.get = AsyncMock(  # type: ignore[method-assign]
            return_value=Run(
                id="run-123",
                strategy_id="test-strategy",
                mode=RunMode.PAPER,
                status=RunStatus.RUNNING,
                symbols=["BTC/USD"],
                timeframe="1m",
                config=None,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )
        event = make_envelope(type_="strategy.FetchWindow")

        await router.route(event)

        routed = cast(AsyncMock, router._event_log).append.call_args[0][0]
        assert routed.type == "live.FetchWindow"

    async def test_routes_to_live_for_live_mode(self, router: DomainRouter) -> None:
        """strategy.* → live.* for live trading runs."""
        router._run_manager.get = AsyncMock(  # type: ignore[method-assign]
            return_value=Run(
                id="run-123",
                strategy_id="test-strategy",
                mode=RunMode.LIVE,
                status=RunStatus.RUNNING,
                symbols=["BTC/USD"],
                timeframe="1m",
                config=None,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )
        event = make_envelope(type_="strategy.PlaceRequest")

        await router.route(event)

        routed = cast(AsyncMock, router._event_log).append.call_args[0][0]
        assert routed.type == "live.PlaceOrder"

    async def test_preserves_causation_chain(self, router: DomainRouter) -> None:
        """Routed event has correct causation_id linking to source."""
        event = make_envelope(type_="strategy.FetchWindow")

        await router.route(event)

        routed = cast(AsyncMock, router._event_log).append.call_args[0][0]
        assert routed.causation_id == event.id

    async def test_preserves_correlation_id(self, router: DomainRouter) -> None:
        """Routed event preserves corr_id from source."""
        event = Envelope(
            id="evt-456",
            type="strategy.FetchWindow",
            payload={},
            run_id="run-123",
            corr_id="corr-789",
            producer="test",
        )

        await router.route(event)

        routed = cast(AsyncMock, router._event_log).append.call_args[0][0]
        assert routed.corr_id == "corr-789"

    async def test_sets_producer_to_router(self, router: DomainRouter) -> None:
        """Routed event has producer set to glados.router."""
        event = make_envelope(type_="strategy.FetchWindow")

        await router.route(event)

        routed = cast(AsyncMock, router._event_log).append.call_args[0][0]
        assert routed.producer == "glados.router"


class TestDomainRouterEventTypes:
    """Tests for supported event type mappings."""

    @pytest_asyncio.fixture
    async def backtest_router(self) -> DomainRouter:
        """Create router for backtest run."""
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        mock_run_manager = AsyncMock()
        mock_run_manager.get = AsyncMock(
            return_value=Run(
                id="run-123",
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                status=RunStatus.RUNNING,
                symbols=["BTC/USD"],
                timeframe="1m",
                config=None,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )

        return DomainRouter(
            event_log=mock_event_log,
            run_manager=mock_run_manager,
        )

    async def test_maps_all_strategy_event_types(
        self, backtest_router: DomainRouter
    ) -> None:
        """All strategy.* events are mapped correctly."""
        event_types = [
            ("strategy.FetchWindow", "backtest.FetchWindow"),
            ("strategy.PlaceRequest", "backtest.PlaceOrder"),
        ]

        for source_type, expected_type in event_types:
            event = make_envelope(type_=source_type)
            await backtest_router.route(event)

            routed = cast(AsyncMock, backtest_router._event_log).append.call_args[0][0]
            assert routed.type == expected_type, f"Failed for {source_type}"
