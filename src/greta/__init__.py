"""Greta - Backtest Data & Simulation

Handles backtesting domain operations:
- Historical data windows
- Fill simulation (slippage, fees)
- Performance statistics calculation

Responds to backtest.* events and emits data.*/orders.* events.
Shares the same contracts as Veda - only execution domain differs.
"""

from src.greta.fill_simulator import DefaultFillSimulator
from src.greta.greta_service import GretaService
from src.greta.models import (
    BacktestResult,
    BacktestStats,
    FillSimulationConfig,
    SimulatedFill,
    SimulatedPosition,
)

__all__ = [
    "DefaultFillSimulator",
    "GretaService",
    "BacktestResult",
    "BacktestStats",
    "FillSimulationConfig",
    "SimulatedFill",
    "SimulatedPosition",
]
