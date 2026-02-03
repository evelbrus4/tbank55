"""
Модель инструмента (акции, фьючерса и т.д.).
Представляет торговый инструмент с его характеристиками.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Instrument:
    """
    Модель торгового инструмента.
    Содержит основные характеристики инструмента для торговли.
    """
    figi: str
    ticker: str
    name: str
    lot: int
    currency: str
    country_of_risk: str
    exchange: str
    instrument_type: str
    api_trade_available: bool
    min_price_increment: float
    short_enabled: bool = False
    
    @property
    def is_tradeable(self) -> bool:
        """Проверяет, доступен ли инструмент для торговли"""
        return self.api_trade_available
