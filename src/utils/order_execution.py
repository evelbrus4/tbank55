"""
Модуль для симуляции задержки исполнения ордеров.
Реалистичная торговля включает задержку между сигналом и исполнением ордера.
"""

import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass, field


@dataclass
class PendingOrder:
    """
    Класс для представления отложенного ордера.
    Хранит информацию об ордере, ожидающем исполнения.
    """
    order_id: str
    ticker: str
    target_lots: int
    expected_price: Decimal
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    figi: Optional[str]
    created_at: datetime
    execute_at: datetime
    direction: Literal['buy', 'sell', 'close']
    status: str = 'pending'  # pending, executed, cancelled
    actual_price: Optional[Decimal] = None
    executed_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None


class OrderExecutionSimulator:
    """
    Класс для симуляции реалистичной задержки исполнения ордеров.
    
    Особенности:
    - Задержка 1-3 секунды между созданием и исполнением ордера
    - Цена может измениться за время задержки
    - Возможность отмены ордера при сильном движении цены
    - Очередь ордеров для обработки
    """
    
    def __init__(
        self,
        min_delay_seconds: float = 1.0,
        max_delay_seconds: float = 3.0,
        max_price_deviation_percent: float = 1.0
    ):
        """
        Инициализация симулятора исполнения ордеров.
        
        Args:
            min_delay_seconds: Минимальная задержка в секундах (по умолчанию 1.0)
            max_delay_seconds: Максимальная задержка в секундах (по умолчанию 3.0)
            max_price_deviation_percent: Максимальное отклонение цены для отмены ордера (по умолчанию 1.0%)
        """
        self.min_delay = min_delay_seconds
        self.max_delay = max_delay_seconds
        self.max_deviation = max_price_deviation_percent / 100.0
        self.pending_orders: Dict[str, PendingOrder] = {}
        self.order_counter = 0
    
    def create_order(
        self,
        ticker: str,
        target_lots: int,
        expected_price: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        figi: Optional[str] = None
    ) -> str:
        """
        Создает новый ордер и добавляет его в очередь на исполнение.
        
        Args:
            ticker: Тикер инструмента
            target_lots: Целевое количество лотов
            expected_price: Ожидаемая цена исполнения
            stop_loss: Уровень стоп-лосса
            take_profit: Уровень тейк-профита
            figi: FIGI инструмента
            
        Returns:
            ID созданного ордера
        """
        self.order_counter += 1
        order_id = f"ORD_{self.order_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Определяем направление
        if target_lots == 0:
            direction = 'close'
        elif target_lots < 0:
            direction = 'buy'  # Long позиция (отрицательные лоты)
        else:
            direction = 'sell'  # Short позиция (положительные лоты)
        
        # Случайная задержка
        delay = random.uniform(self.min_delay, self.max_delay)
        created_at = datetime.now()
        execute_at = created_at + timedelta(seconds=delay)
        
        order = PendingOrder(
            order_id=order_id,
            ticker=ticker,
            target_lots=target_lots,
            expected_price=expected_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            figi=figi,
            created_at=created_at,
            execute_at=execute_at,
            direction=direction
        )
        
        self.pending_orders[order_id] = order
        return order_id
    
    def check_ready_orders(self, current_prices: Dict[str, Decimal]) -> list:
        """
        Проверяет, какие ордера готовы к исполнению.
        
        Args:
            current_prices: Словарь текущих цен по тикерам
            
        Returns:
            Список ордеров, готовых к исполнению
        """
        ready_orders = []
        current_time = datetime.now()
        
        for order_id, order in list(self.pending_orders.items()):
            if order.status != 'pending':
                continue
            
            # Проверяем, пришло ли время исполнения
            if current_time >= order.execute_at:
                current_price = current_prices.get(order.ticker)
                
                if current_price is None:
                    # Нет текущей цены - отменяем ордер
                    order.status = 'cancelled'
                    order.cancellation_reason = 'no_current_price'
                    continue
                
                # Проверяем отклонение цены
                price_deviation = abs(current_price - order.expected_price) / order.expected_price
                
                if price_deviation > self.max_deviation:
                    # Цена слишком сильно изменилась - отменяем ордер
                    order.status = 'cancelled'
                    order.cancellation_reason = f'price_deviation_{float(price_deviation * 100):.2f}%'
                    continue
                
                # Ордер готов к исполнению
                order.actual_price = current_price
                order.status = 'ready'
                ready_orders.append(order)
        
        return ready_orders
    
    def execute_order(self, order_id: str) -> Optional[PendingOrder]:
        """
        Помечает ордер как исполненный.
        
        Args:
            order_id: ID ордера
            
        Returns:
            Исполненный ордер или None
        """
        order = self.pending_orders.get(order_id)
        if order and order.status == 'ready':
            order.status = 'executed'
            order.executed_at = datetime.now()
            return order
        return None
    
    def cancel_order(self, order_id: str, reason: str = 'manual') -> bool:
        """
        Отменяет ордер.
        
        Args:
            order_id: ID ордера
            reason: Причина отмены
            
        Returns:
            True если ордер был отменен, False иначе
        """
        order = self.pending_orders.get(order_id)
        if order and order.status == 'pending':
            order.status = 'cancelled'
            order.cancellation_reason = reason
            return True
        return False
    
    def get_pending_orders_count(self) -> int:
        """
        Возвращает количество ордеров в очереди.
        
        Returns:
            Количество ордеров со статусом 'pending'
        """
        return sum(1 for order in self.pending_orders.values() if order.status == 'pending')
    
    def get_order_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает информацию об ордере.
        
        Args:
            order_id: ID ордера
            
        Returns:
            Словарь с информацией об ордере или None
        """
        order = self.pending_orders.get(order_id)
        if not order:
            return None
        
        return {
            'order_id': order.order_id,
            'ticker': order.ticker,
            'target_lots': order.target_lots,
            'expected_price': float(order.expected_price),
            'actual_price': float(order.actual_price) if order.actual_price else None,
            'direction': order.direction,
            'status': order.status,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'execute_at': order.execute_at.strftime('%Y-%m-%d %H:%M:%S'),
            'executed_at': order.executed_at.strftime('%Y-%m-%d %H:%M:%S') if order.executed_at else None,
            'delay_seconds': (order.execute_at - order.created_at).total_seconds(),
            'cancellation_reason': order.cancellation_reason
        }
    
    def cleanup_old_orders(self, max_age_hours: int = 24):
        """
        Удаляет старые исполненные/отмененные ордера.
        
        Args:
            max_age_hours: Максимальный возраст ордеров в часах
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        orders_to_remove = [
            order_id for order_id, order in self.pending_orders.items()
            if order.status in ['executed', 'cancelled'] and order.created_at < cutoff_time
        ]
        
        for order_id in orders_to_remove:
            del self.pending_orders[order_id]
