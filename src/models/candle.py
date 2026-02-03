"""
Модель свечи (OHLCV данные).
Представляет ценовые данные за определенный временной интервал.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Candle:
    """
    Модель свечи с OHLCV данными.
    Содержит информацию о цене и объеме за временной интервал.
    """
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    figi: str
    interval: str
    is_complete: bool = True
    
    @property
    def body(self) -> float:
        """Размер тела свечи"""
        return abs(self.close - self.open)
    
    @property
    def is_bullish(self) -> bool:
        """Проверяет, является ли свеча бычьей"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Проверяет, является ли свеча медвежьей"""
        return self.close < self.open
    
    @property
    def upper_shadow(self) -> float:
        """Размер верхней тени"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """Размер нижней тени"""
        return min(self.open, self.close) - self.low
