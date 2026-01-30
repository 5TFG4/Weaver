"""
Smoke Tests for Test Infrastructure

These tests verify that the test infrastructure itself is working correctly.
Run these first to ensure pytest and fixtures are properly configured.
"""

from datetime import datetime, timezone

import pytest


class TestTestInfrastructure:
    """Verify basic test infrastructure is working."""
    
    def test_pytest_runs(self) -> None:
        """Verify pytest can run tests."""
        assert True
    
    def test_fixtures_available(self, frozen_time: datetime) -> None:
        """Verify fixtures from conftest.py are available."""
        assert frozen_time is not None
        assert isinstance(frozen_time, datetime)
    
    def test_sample_ids_available(
        self,
        sample_run_id: str,
        sample_order_id: str,
        sample_corr_id: str,
    ) -> None:
        """Verify ID fixtures are available."""
        assert sample_run_id.startswith("run-")
        assert sample_order_id.startswith("order-")
        assert sample_corr_id.startswith("corr-")


class TestControllableClock:
    """Test the ControllableClock fixture."""
    
    def test_clock_creation(self) -> None:
        """Verify ControllableClock can be created."""
        from tests.fixtures.clock import ControllableClock
        
        start = datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc)
        clock = ControllableClock(start_time=start)
        
        assert clock.current_time == start
        assert clock.tick_count == 0
    
    def test_clock_advance(self) -> None:
        """Verify clock can advance and emit ticks."""
        from tests.fixtures.clock import ControllableClock
        
        start = datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc)
        clock = ControllableClock(start_time=start, timeframe="1m")
        
        ticks = clock.advance(3)
        
        assert len(ticks) == 3
        assert clock.tick_count == 3
        assert ticks[0].ts == datetime(2024, 1, 15, 9, 31, tzinfo=timezone.utc)
        assert ticks[1].ts == datetime(2024, 1, 15, 9, 32, tzinfo=timezone.utc)
        assert ticks[2].ts == datetime(2024, 1, 15, 9, 33, tzinfo=timezone.utc)
    
    def test_clock_callback(self) -> None:
        """Verify clock callbacks are called on tick."""
        from tests.fixtures.clock import ClockTick, ControllableClock
        
        start = datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc)
        clock = ControllableClock(start_time=start)
        
        received: list[ClockTick] = []
        clock.on_tick(lambda tick: received.append(tick))
        
        clock.advance(2)
        
        assert len(received) == 2


class TestInMemoryEventLog:
    """Test the InMemoryEventLog fixture."""
    
    def test_event_log_creation(self) -> None:
        """Verify InMemoryEventLog can be created."""
        from tests.fixtures.event_log import InMemoryEventLog
        
        log = InMemoryEventLog()
        assert log.event_count == 0
    
    def test_event_log_append(self) -> None:
        """Verify events can be appended."""
        from tests.fixtures.event_log import InMemoryEventLog, TestEnvelope
        
        log = InMemoryEventLog()
        event = TestEnvelope.create("test.Event", {"key": "value"})
        
        log.append(event)
        
        assert log.event_count == 1
        assert log.events[0].type == "test.Event"
    
    def test_event_log_subscribe(self) -> None:
        """Verify subscription pattern matching works."""
        from tests.fixtures.event_log import InMemoryEventLog, TestEnvelope
        
        log = InMemoryEventLog()
        received: list[TestEnvelope] = []
        
        log.subscribe("orders.*", lambda e: received.append(e))
        
        log.append(TestEnvelope.create("orders.Placed", {}))
        log.append(TestEnvelope.create("strategy.FetchWindow", {}))
        log.append(TestEnvelope.create("orders.Filled", {}))
        
        assert len(received) == 2
        assert received[0].type == "orders.Placed"
        assert received[1].type == "orders.Filled"


class TestFactories:
    """Test the factory modules."""
    
    def test_event_factory(self) -> None:
        """Verify EventFactory works."""
        from tests.factories.events import EventFactory, create_event
        
        # Using class method
        event1 = EventFactory.create("orders.Placed", {"order_id": "123"})
        assert event1["type"] == "orders.Placed"
        assert event1["payload"]["order_id"] == "123"
        
        # Using convenience function
        event2 = create_event("orders.Filled", {"qty": 100})
        assert event2["type"] == "orders.Filled"
    
    def test_order_factory(self) -> None:
        """Verify OrderFactory works."""
        from tests.factories.orders import OrderFactory, create_order
        
        # Using class method
        order1 = OrderFactory.create("AAPL", "buy", 100)
        assert order1["symbol"] == "AAPL"
        assert order1["side"] == "buy"
        
        # Using convenience function
        order2 = create_order("BTCUSD", "sell", 0.5)
        assert order2["symbol"] == "BTCUSD"
    
    def test_run_factory(self) -> None:
        """Verify RunFactory works."""
        from tests.factories.runs import RunFactory, create_run
        
        # Using class method
        run1 = RunFactory.create("sma_cross", mode="live")
        assert run1["strategy_name"] == "sma_cross"
        assert run1["mode"] == "live"
        
        # Using convenience function
        run2 = create_run("momentum", mode="backtest")
        assert run2["mode"] == "backtest"


class TestAsyncSupport:
    """Test async test support."""
    
    @pytest.mark.asyncio
    async def test_async_test_runs(self) -> None:
        """Verify async tests work."""
        import asyncio
        
        await asyncio.sleep(0.001)
        assert True
    
    @pytest.mark.asyncio
    async def test_async_fixture_works(self, async_timeout: float) -> None:
        """Verify async fixtures work."""
        assert async_timeout == 5.0
