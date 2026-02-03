"""
Модуль для симуляции проскальзывания (slippage) при исполнении ордеров.
Проскальзывание - это разница между ожидаемой ценой исполнения и фактической ценой.
"""

import random
from decimal import Decimal
from typing import Literal


class SlippageSimulator:
    """
    Класс для симуляции реалистичного проскальзывания при исполнении ордеров.
    
    Проскальзывание зависит от:
    - Базового уровня (0.01-0.02%)
    - Размера позиции (больше позиция = больше проскальзывание)
    - Волатильности рынка (выше ATR = больше проскальзывание)
    
    Проскальзывание всегда негативно для трейдера:
    - При покупке цена выше ожидаемой
    - При продаже цена ниже ожидаемой
    """
    
    def __init__(
        self,
        base_slippage_percent: float = 0.02,
        volume_factor_per_10_lots: float = 0.01,
        volatility_multiplier: float = 2.0,
        max_slippage_percent: float = 0.5
    ):
        """
        Инициализация симулятора проскальзывания.
        
        Args:
            base_slippage_percent: Базовое проскальзывание в процентах (по умолчанию 0.02%)
            volume_factor_per_10_lots: Дополнительное проскальзывание за каждые 10 лотов (по умолчанию 0.01%)
            volatility_multiplier: Множитель для волатильности (по умолчанию 2.0)
            max_slippage_percent: Максимальное проскальзывание в процентах (по умолчанию 0.5%)
        """
        self.base_slippage = base_slippage_percent / 100.0
        self.volume_factor = volume_factor_per_10_lots / 100.0
        self.volatility_multiplier = volatility_multiplier
        self.max_slippage = max_slippage_percent / 100.0
    
    def calculate_slippage(
        self,
        expected_price: Decimal,
        lots: int,
        direction: Literal['buy', 'sell'],
        atr: float = None,
        avg_atr: float = None
    ) -> Decimal:
        """
        Рассчитывает фактическую цену исполнения с учетом проскальзывания.
        
        Args:
            expected_price: Ожидаемая цена исполнения
            lots: Количество лотов (по модулю)
            direction: Направление сделки ('buy' или 'sell')
            atr: Текущий ATR (Average True Range) для учета волатильности
            avg_atr: Средний ATR для сравнения
            
        Returns:
            Фактическая цена исполнения с учетом проскальзывания
        """
        abs_lots = abs(lots)
        
        # 1. Базовое проскальзывание
        slippage = self.base_slippage
        
        # 2. Добавляем проскальзывание за объем
        # За каждые 10 лотов добавляем volume_factor
        volume_slippage = (abs_lots // 10) * self.volume_factor
        slippage += volume_slippage
        
        # 3. Добавляем проскальзывание за волатильность
        if atr is not None and avg_atr is not None and avg_atr > 0:
            # Если текущий ATR выше среднего, увеличиваем проскальзывание
            volatility_ratio = atr / avg_atr
            if volatility_ratio > 1.0:
                volatility_slippage = (volatility_ratio - 1.0) * self.base_slippage * self.volatility_multiplier
                slippage += volatility_slippage
        
        # 4. Ограничиваем максимальное проскальзывание
        slippage = min(slippage, self.max_slippage)
        
        # 5. Добавляем случайность (±20% от расчетного проскальзывания)
        random_factor = random.uniform(0.8, 1.2)
        slippage *= random_factor
        
        # 6. Применяем проскальзывание в зависимости от направления
        # Проскальзывание всегда негативно для трейдера
        if direction == 'buy':
            # При покупке цена увеличивается
            actual_price = expected_price * (Decimal("1") + Decimal(str(slippage)))
        else:  # sell
            # При продаже цена уменьшается
            actual_price = expected_price * (Decimal("1") - Decimal(str(slippage)))
        
        return actual_price
    
    def get_slippage_info(
        self,
        expected_price: Decimal,
        actual_price: Decimal,
        lots: int
    ) -> dict:
        """
        Возвращает информацию о проскальзывании для логирования.
        
        Args:
            expected_price: Ожидаемая цена
            actual_price: Фактическая цена
            lots: Количество лотов
            
        Returns:
            Словарь с информацией о проскальзывании
        """
        slippage_amount = actual_price - expected_price
        slippage_percent = (slippage_amount / expected_price) * Decimal("100")
        total_slippage_cost = slippage_amount * Decimal(str(abs(lots)))
        
        return {
            'expected_price': float(expected_price),
            'actual_price': float(actual_price),
            'slippage_amount': float(slippage_amount),
            'slippage_percent': float(slippage_percent),
            'total_slippage_cost': float(total_slippage_cost),
            'lots': abs(lots)
        }
