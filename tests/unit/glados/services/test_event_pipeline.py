"""
Tests for Event Pipeline Wiring — M8-P1 Package B

TDD tests for:
- B.1: PostgresEventLog direct subscriber dispatch (D-1)
- B.2: DomainRouter wiring in app lifespan (D-4)
- B.3: InMemoryEventLog fallback in no-DB mode
- B.4: SSE subscriber integration (event → subscriber → broadcaster)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.events.log import InMemoryEventLog
from src.events.protocol import Envelope


# =============================================================================
# B.1: PostgresEventLog Direct Subscriber Dispatch (D-1)
# =============================================================================


class TestPostgresEventLogDirectDispatch:
    """
    D-1: PostgresEventLog.append() must dispatch to in-process subscribers
    directly (same as InMemoryEventLog), in addition to pg_notify().
    """

    async def test_append_fires_legacy_subscriber_callbacks(self) -> None:
        """After DB write, legacy subscribers (via subscribe()) should fire."""
        from src.events.log import PostgresEventLog

        # Create PostgresEventLog with mocked session factory
        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.id = 42
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        # Make the session context manager work
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        event_log = PostgresEventLog(session_factory=mock_session_factory)

        # Subscribe a callback
        received = []

        async def on_event(envelope: Envelope) -> None:
            received.append(envelope)

        await event_log.subscribe(on_event)

        # Append an event
        envelope = Envelope(
            type="test.Event",
            producer="test",
            payload={"key": "value"},
        )

        with patch("src.walle.models.OutboxEvent", return_value=mock_event):
            await event_log.append(envelope)

        # Legacy subscriber MUST fire directly (D-1 requirement)
        assert len(received) == 1
        assert received[0].type == "test.Event"

    async def test_append_fires_filtered_subscriber_callbacks(self) -> None:
        """After DB write, filtered subscribers should fire for matching events."""
        from src.events.log import PostgresEventLog

        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.id = 42
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        event_log = PostgresEventLog(session_factory=mock_session_factory)

        # Subscribe filtered
        received = []

        async def on_event(envelope: Envelope) -> None:
            received.append(envelope)

        await event_log.subscribe_filtered(
            event_types=["orders.Created"],
            callback=on_event,
        )

        # Append matching event
        matching = Envelope(type="orders.Created", producer="test", payload={})
        # Append non-matching event
        non_matching = Envelope(type="run.Started", producer="test", payload={})

        with patch("src.walle.models.OutboxEvent", return_value=mock_event):
            await event_log.append(matching)
            await event_log.append(non_matching)

        # Only matching event should be received
        assert len(received) == 1
        assert received[0].type == "orders.Created"

    async def test_subscriber_error_does_not_block_others(self) -> None:
        """One subscriber's error should not prevent others from receiving."""
        from src.events.log import PostgresEventLog

        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.id = 42
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        event_log = PostgresEventLog(session_factory=mock_session_factory)

        received = []

        async def bad_subscriber(envelope: Envelope) -> None:
            raise RuntimeError("subscriber crash")

        async def good_subscriber(envelope: Envelope) -> None:
            received.append(envelope)

        await event_log.subscribe(bad_subscriber)
        await event_log.subscribe(good_subscriber)

        envelope = Envelope(type="test.Event", producer="test", payload={})

        with patch("src.walle.models.OutboxEvent", return_value=mock_event):
            await event_log.append(envelope)

        # Good subscriber should still receive despite bad subscriber error
        assert len(received) == 1

    async def test_behavioral_parity_with_in_memory(self) -> None:
        """
        N-07: PostgresEventLog and InMemoryEventLog must behave identically
        for in-process subscriber dispatch.
        """
        # Test InMemoryEventLog behavior as baseline
        in_memory = InMemoryEventLog()
        memory_received = []

        async def on_memory(e: Envelope) -> None:
            memory_received.append(e)

        await in_memory.subscribe(on_memory)

        envelope = Envelope(type="test.Event", producer="test", payload={"a": 1})
        await in_memory.append(envelope)

        assert len(memory_received) == 1
        assert memory_received[0].type == "test.Event"

        # PostgresEventLog should produce the same behavior
        from src.events.log import PostgresEventLog

        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.id = 1
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_sf = MagicMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        postgres = PostgresEventLog(session_factory=mock_sf)
        pg_received = []

        async def on_pg(e: Envelope) -> None:
            pg_received.append(e)

        await postgres.subscribe(on_pg)

        with patch("src.walle.models.OutboxEvent", return_value=mock_event):
            await postgres.append(envelope)

        # Both should dispatch to subscribers
        assert len(pg_received) == len(memory_received)
        assert pg_received[0].type == memory_received[0].type


# =============================================================================
# B.2: DomainRouter Wiring in App Lifespan (D-4)
# =============================================================================


class TestDomainRouterWiring:
    """D-4: DomainRouter should be wired as standalone singleton in lifespan."""

    async def test_domain_router_routes_strategy_to_backtest(self) -> None:
        """strategy.FetchWindow should route to backtest.FetchWindow for backtest runs."""
        from src.events.log import InMemoryEventLog
        from src.glados.schemas import RunCreate, RunMode
        from src.glados.services.domain_router import DomainRouter
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        run_manager = create_run_manager_with_deps(event_log=event_log)

        # Create a backtest run
        run = await run_manager.create(RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.BACKTEST,
            symbols=["AAPL"],
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-06-30T00:00:00Z",
        ))

        router = DomainRouter(event_log=event_log, run_manager=run_manager)

        # Subscribe to capture routed events
        routed = []

        async def on_routed(e: Envelope) -> None:
            routed.append(e)

        await event_log.subscribe(on_routed)

        # Emit a strategy.FetchWindow event
        strategy_event = Envelope(
            type="strategy.FetchWindow",
            producer="marvin.runner",
            run_id=run.id,
            payload={"symbol": "AAPL", "timeframe": "1m"},
        )

        await router.route(strategy_event)

        # Should be routed to backtest.FetchWindow
        fetch_events = [e for e in routed if e.type == "backtest.FetchWindow"]
        assert len(fetch_events) == 1
        assert fetch_events[0].run_id == run.id
        assert fetch_events[0].payload["symbol"] == "AAPL"

    async def test_domain_router_routes_strategy_to_live(self) -> None:
        """strategy.PlaceRequest should route to live.PlaceOrder for live runs."""
        from src.events.log import InMemoryEventLog
        from src.glados.schemas import RunCreate, RunMode
        from src.glados.services.domain_router import DomainRouter
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        run_manager = create_run_manager_with_deps(event_log=event_log)

        run = await run_manager.create(RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.LIVE,
            symbols=["AAPL"],
        ))

        router = DomainRouter(event_log=event_log, run_manager=run_manager)

        routed = []

        async def on_routed(e: Envelope) -> None:
            routed.append(e)

        await event_log.subscribe(on_routed)

        strategy_event = Envelope(
            type="strategy.PlaceRequest",
            producer="marvin.runner",
            run_id=run.id,
            payload={"symbol": "AAPL", "side": "buy", "qty": "10"},
        )

        await router.route(strategy_event)

        # Should be routed to live.PlaceOrder
        place_events = [e for e in routed if e.type == "live.PlaceOrder"]
        assert len(place_events) == 1
        assert place_events[0].run_id == run.id

    async def test_domain_router_ignores_non_strategy_events(self) -> None:
        """DomainRouter should ignore events not starting with 'strategy.'."""
        from src.events.log import InMemoryEventLog
        from src.glados.services.domain_router import DomainRouter
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        run_manager = create_run_manager_with_deps(event_log=event_log)

        router = DomainRouter(event_log=event_log, run_manager=run_manager)

        initial_count = event_log.event_count

        non_strategy = Envelope(
            type="orders.Created",
            producer="veda",
            payload={"order_id": "123"},
        )
        await router.route(non_strategy)

        # No new events should have been appended
        assert event_log.event_count == initial_count


# =============================================================================
# B.3: InMemoryEventLog in No-DB Mode
# =============================================================================


class TestInMemoryEventLogFallback:
    """B.3: When no DB_URL, app should create InMemoryEventLog instead of None."""

    def test_app_without_db_creates_in_memory_event_log(self) -> None:
        """create_app without DB_URL should have InMemoryEventLog."""
        import os

        from fastapi.testclient import TestClient

        from src.config import get_test_config
        from src.glados.app import create_app

        settings = get_test_config()
        app = create_app(settings=settings)

        # Temporarily unset DB_URL to simulate no-database mode
        old_db_url = os.environ.pop("DB_URL", None)
        try:
            with TestClient(app) as client:
                # event_log should exist (not None)
                assert app.state.event_log is not None
                assert isinstance(app.state.event_log, InMemoryEventLog)
        finally:
            if old_db_url is not None:
                os.environ["DB_URL"] = old_db_url

    def test_app_without_db_run_manager_has_event_log(self) -> None:
        """RunManager should have event_log even without DB."""
        import os

        from fastapi.testclient import TestClient

        from src.config import get_test_config
        from src.glados.app import create_app

        settings = get_test_config()
        app = create_app(settings=settings)

        old_db_url = os.environ.pop("DB_URL", None)
        try:
            with TestClient(app) as client:
                run_manager = app.state.run_manager
                assert run_manager._event_log is not None
        finally:
            if old_db_url is not None:
                os.environ["DB_URL"] = old_db_url

    def test_app_without_db_sse_broadcaster_subscribed(self) -> None:
        """SSEBroadcaster should be subscribed to InMemoryEventLog."""
        import os

        from fastapi.testclient import TestClient

        from src.config import get_test_config
        from src.glados.app import create_app

        settings = get_test_config()
        app = create_app(settings=settings)

        old_db_url = os.environ.pop("DB_URL", None)
        try:
            with TestClient(app) as client:
                event_log = app.state.event_log
                assert isinstance(event_log, InMemoryEventLog)
                # Verify broadcaster is subscribed (has at least one subscriber)
                assert len(event_log._subscribers) >= 1
        finally:
            if old_db_url is not None:
                os.environ["DB_URL"] = old_db_url


# =============================================================================
# B.4: Event → Subscriber → SSEBroadcaster Integration
# =============================================================================


class TestEventToSSEIntegration:
    """B.4: Events appended to EventLog should reach SSEBroadcaster."""

    async def test_appended_event_reaches_broadcaster(self) -> None:
        """InMemoryEventLog → subscriber → SSEBroadcaster.publish()."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        event_log = InMemoryEventLog()
        broadcaster = SSEBroadcaster()

        # Wire broadcaster as subscriber (same as app lifespan does)
        published = []

        async def on_event(envelope: Envelope) -> None:
            await broadcaster.publish(envelope.type, envelope.payload)
            published.append(envelope)

        await event_log.subscribe(on_event)

        # Append an event
        envelope = Envelope(
            type="run.Started",
            producer="glados.run_manager",
            payload={"run_id": "run-1", "status": "running"},
        )
        await event_log.append(envelope)

        # Event should have reached the broadcaster
        assert len(published) == 1
        assert published[0].type == "run.Started"

    async def test_domain_router_event_reaches_broadcaster(self) -> None:
        """DomainRouter routed event → EventLog → SSEBroadcaster chain."""
        from src.glados.schemas import RunCreate, RunMode
        from src.glados.services.domain_router import DomainRouter
        from src.glados.sse_broadcaster import SSEBroadcaster
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        broadcaster = SSEBroadcaster()
        run_manager = create_run_manager_with_deps(event_log=event_log)

        # Create a backtest run
        run = await run_manager.create(RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.BACKTEST,
            symbols=["AAPL"],
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-06-30T00:00:00Z",
        ))

        router = DomainRouter(event_log=event_log, run_manager=run_manager)

        # Wire broadcaster
        broadcasted = []

        async def on_event(envelope: Envelope) -> None:
            await broadcaster.publish(envelope.type, envelope.payload)
            broadcasted.append(envelope)

        await event_log.subscribe(on_event)

        # Route a strategy event
        strategy_event = Envelope(
            type="strategy.FetchWindow",
            producer="marvin.runner",
            run_id=run.id,
            payload={"symbol": "AAPL"},
        )
        await router.route(strategy_event)

        # The routed event should reach the broadcaster
        fetch_events = [e for e in broadcasted if e.type == "backtest.FetchWindow"]
        assert len(fetch_events) == 1


class TestRouteToHandlerClosedLoop:
    """F-01: strategy.PlaceRequest should reach backtest order handler via routing chain."""

    async def test_strategy_place_request_reaches_greta_handler(self) -> None:
        """strategy.PlaceRequest -> DomainRouter -> backtest.PlaceOrder -> GretaService.place_order."""
        from datetime import UTC, datetime
        from unittest.mock import AsyncMock

        from src.glados.schemas import RunMode, RunStatus
        from src.glados.services.domain_router import DomainRouter
        from src.glados.services.run_manager import Run
        from src.greta.greta_service import GretaService

        event_log = InMemoryEventLog()

        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=[])
        greta = GretaService(
            run_id="run-123",
            bar_repository=mock_bar_repo,
            event_log=event_log,
        )
        await greta.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        run = Run(
            id="run-123",
            strategy_id="test-strategy",
            mode=RunMode.BACKTEST,
            status=RunStatus.RUNNING,
            symbols=["BTC/USD"],
            timeframe="1m",
            config=None,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        mock_run_manager = AsyncMock()
        mock_run_manager.get = AsyncMock(return_value=run)

        router = DomainRouter(event_log=event_log, run_manager=mock_run_manager)

        strategy_event = Envelope(
            type="strategy.PlaceRequest",
            producer="marvin.runner",
            run_id="run-123",
            payload={
                "symbol": "BTC/USD",
                "side": "buy",
                "qty": "1.0",
                "order_type": "market",
            },
        )
        await router.route(strategy_event)

        await asyncio.sleep(0)

        assert len(greta.pending_orders) == 1


class TestLiveFetchWindowClosedLoop:
    """Closed-loop proof for live.FetchWindow consumer wiring."""

    def test_live_fetch_window_emits_data_window_ready(self) -> None:
        """live.FetchWindow appended to app event log should produce data.WindowReady."""
        import os

        from fastapi.testclient import TestClient

        from src.config import get_test_config
        from src.glados.app import create_app

        settings = get_test_config()
        app = create_app(settings=settings)

        old_db_url = os.environ.pop("DB_URL", None)
        try:
            with TestClient(app):
                event_log = app.state.event_log
                captured: list[Envelope] = []

                async def on_event(envelope: Envelope) -> None:
                    captured.append(envelope)

                import asyncio

                asyncio.run(event_log.subscribe(on_event))

                fetch_event = Envelope(
                    type="live.FetchWindow",
                    producer="test",
                    run_id="run-live-1",
                    payload={
                        "symbol": "BTC/USD",
                        "lookback": 3,
                    },
                )
                asyncio.run(event_log.append(fetch_event))

                produced = [e for e in captured if e.type == "data.WindowReady"]
                assert len(produced) >= 1
                assert produced[-1].payload["symbol"] == "BTC/USD"
                assert produced[-1].payload["lookback"] == 3
                assert isinstance(produced[-1].payload["bars"], list)
        finally:
            if old_db_url is not None:
                os.environ["DB_URL"] = old_db_url
