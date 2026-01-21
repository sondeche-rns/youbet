"""
Professional Sports Betting Algorithm
"""

__version__ = "2.0.0"

from .algorithm import ProfessionalBettingAlgorithm
from .data_collector import HistoricalDataCollector
from .backtest import BacktestEngine

__all__ = [
    'ProfessionalBettingAlgorithm',
    'HistoricalDataCollector',
    'BacktestEngine'
]
