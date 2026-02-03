"""
Модуль для расчета спреда bid/ask при торговле фьючерсами.
Спред - это разница между ценой покупки (ask) и ценой продажи (bid).
"""

from decimal import Decimal
from typing import Tuple


class SpreadCalculator:
    """
    Класс для расчета реалистичного спреда bid/ask для фьючерсов.
    
    Спред зависит от:
    - Базового уровня (0.01-0.05% от цены)
    - Волатильности рынка (выше ATR = больше спред)
    - Минимального шага цены (min_price_increment)
    
    При торговле:
    - Покупка происходит по ask (цена + спред/2)
    - Продажа происходит по bid (цена - спред/2)
    """
    
    def __init__(
        self,
        base_spread_percent: float = 0.03,
        volatility_multiplier: float = 1.5,
        min_spread_percent: float = 0.01,
        max_spread_percent: float = 0.1
    ):
        """
        Инициализация калькулятора спреда.
        
        Args:
            base_spread_percent: Базовый спред в процентах (по умолчанию 0.03%)
            volatility_multiplier: Множитель для волатильности (по умолчанию 1.5)
            min_spread_percent: Минимальный спред в процентах (по умолчанию 0.01%)
            max_spread_percent: Максимальный спред в процентах (по умолчанию 0.1%)
        """
        self.base_spread = base_spread_percent / 100.0
        self.volatility_multiplier = volatility_multiplier
        self.min_spread = min_spread_percent / 100.0
        self.max_spread = max_spread_percent / 100.0
    
    def calculate_spread(
        self,
        mid_price: Decimal,
        atr: float = None,
        avg_atr: float = None,
        min_price_increment: Decimal = None
    ) -> Decimal:
        """
        Рассчитывает размер спреда для данной цены.
        
        Args:
            mid_price: Средняя цена (между bid и ask)
            atr: Текущий ATR для учета волатильности
            avg_atr: Средний ATR для сравнения
            min_price_increment: Минимальный шаг цены инструмента
            
        Returns:
            Размер спреда в абсолютных единицах
        """
        # 1. Базовый спред
        spread_percent = self.base_spread
        
        # 2. Корректировка на волатильность
        if atr is not None and avg_atr is not None and avg_atr > 0:
            volatility_ratio = atr / avg_atr
            if volatility_ratio > 1.0:
                # Увеличиваем спред при высокой волатильности
                volatility_adjustment = (volatility_ratio - 1.0) * self.base_spread * self.volatility_multiplier
                spread_percent += volatility_adjustment
        
        # 3. Ограничиваем спред
        spread_percent = max(self.min_spread, min(spread_percent, self.max_spread))
        
        # 4. Рассчитываем абсолютный спред
        spread_amount = mid_price * Decimal(str(spread_percent))
        
        # 5. Округляем до минимального шага цены, если указан
        if min_price_increment is not None and min_price_increment > 0:
            # Спред должен быть кратен минимальному шагу
            spread_amount = (spread_amount / min_price_increment).quantize(Decimal('1')) * min_price_increment
            # Минимум 1 шаг
            if spread_amount < min_price_increment:
                spread_amount = min_price_increment
        
        return spread_amount
    
    def get_bid_ask_prices(
        self,
        mid_price: Decimal,
        atr: float = None,
        avg_atr: float = None,
        min_price_increment: Decimal = None
    ) -> Tuple[Decimal, Decimal]:
        """
        Возвращает цены bid и ask на основе средней цены.
        
        Args:
            mid_price: Средняя цена
            atr: Текущий ATR
            avg_atr: Средний ATR
            min_price_increment: Минимальный шаг цены
            
        Returns:
            Tuple[bid_price, ask_price]
        """
        spread = self.calculate_spread(mid_price, atr, avg_atr, min_price_increment)
        half_spread = spread / Decimal("2")
        
        bid_price = mid_price - half_spread
        ask_price = mid_price + half_spread
        
        return bid_price, ask_price
    
    def get_execution_price(
        self,
        mid_price: Decimal,
        direction: str,
        atr: float = None,
        avg_atr: float = None,
        min_price_increment: Decimal = None
    ) -> Decimal:
        """
        Возвращает цену исполнения с учетом спреда.
        
        Args:
            mid_price: Средняя рыночная цена
            direction: Направление сделки ('buy' или 'sell')
            atr: Текущий ATR
            avg_atr: Средний ATR
            min_price_increment: Минимальный шаг цены
            
        Returns:
            Цена исполнения (ask для покупки, bid для продажи)
        """
        bid_price, ask_price = self.get_bid_ask_prices(mid_price, atr, avg_atr, min_price_increment)
        
        if direction == 'buy':
            return ask_price  # Покупаем по ask (дороже)
        else:  # sell
            return bid_price  # Продаем по bid (дешевле)
    
    def get_spread_info(
        self,
        mid_price: Decimal,
        atr: float = None,
        avg_atr: float = None
    ) -> dict:
        """
        Возвращает информацию о спреде для логирования.
        
        Args:
            mid_price: Средняя цена
            atr: Текущий ATR
            avg_atr: Средний ATR
            
        Returns:
            Словарь с информацией о спреде
        """
        bid_price, ask_price = self.get_bid_ask_prices(mid_price, atr, avg_atr)
        spread_amount = ask_price - bid_price
        spread_percent = (spread_amount / mid_price) * Decimal("100")
        
        return {
            'mid_price': float(mid_price),
            'bid_price': float(bid_price),
            'ask_price': float(ask_price),
            'spread_amount': float(spread_amount),
            'spread_percent': float(spread_percent)
        }
