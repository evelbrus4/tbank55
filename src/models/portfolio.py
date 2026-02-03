"""
Модель портфеля.
Представляет состояние торгового портфеля с позициями и балансом.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class Position:
    """
    Модель позиции в портфеле.
    Представляет открытую позицию по инструменту.
    """
    figi: str
    ticker: str
    quantity: int
    average_price: float
    current_price: float
    currency: str
    
    @property
    def market_value(self) -> float:
        """Текущая рыночная стоимость позиции"""
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """Стоимость покупки позиции"""
        return self.quantity * self.average_price
    
    @property
    def unrealized_pnl(self) -> float:
        """Нереализованная прибыль/убыток"""
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_pnl_percent(self) -> float:
        """Нереализованная прибыль/убыток в процентах"""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100


@dataclass
class Portfolio:
    """
    Модель торгового портфеля.
    Содержит информацию о балансе, позициях и общей статистике.
    """
    account_id: str
    cash_balance: float
    currency: str
    positions: Dict[str, Position] = field(default_factory=dict)
    total_invested: float = 0.0
    realized_pnl: float = 0.0
    last_updated: Optional[datetime] = None
    
    @property
    def positions_value(self) -> float:
        """Общая стоимость всех позиций"""
        return sum(pos.market_value for pos in self.positions.values())
    
    @property
    def total_value(self) -> float:
        """Общая стоимость портфеля (кэш + позиции)"""
        return self.cash_balance + self.positions_value
    
    @property
    def unrealized_pnl(self) -> float:
        """Общая нереализованная прибыль/убыток"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    @property
    def total_pnl(self) -> float:
        """Общая прибыль/убыток (реализованная + нереализованная)"""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def total_return_percent(self) -> float:
        """Общая доходность в процентах"""
        if self.total_invested == 0:
            return 0.0
        return (self.total_pnl / self.total_invested) * 100
    
    def add_position(self, position: Position) -> None:
        """Добавляет или обновляет позицию в портфеле"""
        self.positions[position.figi] = position
    
    def remove_position(self, figi: str) -> None:
        """Удаляет позицию из портфеля"""
        if figi in self.positions:
            del self.positions[figi]
    
    def get_position(self, figi: str) -> Optional[Position]:
        """Получает позицию по FIGI"""
        return self.positions.get(figi)
