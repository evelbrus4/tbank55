"""
Модель ордера (заявки на покупку/продажу).
Представляет торговую заявку с её параметрами и статусом.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class OrderDirection(Enum):
    """Направление ордера"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Тип ордера"""
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(Enum):
    """Статус ордера"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """
    Модель торгового ордера.
    Содержит информацию о заявке на покупку или продажу инструмента.
    """
    order_id: str
    figi: str
    direction: OrderDirection
    order_type: OrderType
    quantity: int
    price: Optional[float]
    status: OrderStatus
    created_at: datetime
    executed_at: Optional[datetime] = None
    executed_quantity: int = 0
    executed_price: Optional[float] = None
    commission: float = 0.0
    
    @property
    def is_filled(self) -> bool:
        """Проверяет, исполнен ли ордер полностью"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """Проверяет, активен ли ордер"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def total_cost(self) -> float:
        """Общая стоимость исполненного ордера с комиссией"""
        if self.executed_price and self.executed_quantity:
            return self.executed_price * self.executed_quantity + self.commission
        return 0.0
