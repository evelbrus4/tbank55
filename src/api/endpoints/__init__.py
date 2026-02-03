"""
Эндпоинты для работы с различными разделами API.
Каждый эндпоинт отвечает за определенную группу операций.
"""

from .instruments import InstrumentsEndpoint
from .market_data import MarketDataEndpoint
from .orders import OrdersEndpoint

__all__ = ['InstrumentsEndpoint', 'MarketDataEndpoint', 'OrdersEndpoint']
