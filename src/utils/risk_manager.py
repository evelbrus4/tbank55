"""
Модуль для управления рисками при торговле.
Реализует правила защиты капитала и контроля рисков.
"""

from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta


class RiskManager:
    """
    Класс для управления рисками торгового бота.
    
    Основные функции:
    - Контроль максимальной просадки (max drawdown)
    - Ограничение риска на сделку
    - Ограничение количества открытых позиций
    - Дневной лимит убытков
    - Расчет размера позиции на основе риска
    """
    
    def __init__(
        self,
        max_drawdown_percent: float = 20.0,
        risk_per_trade_percent: float = 2.0,
        max_open_positions: int = 5,
        daily_loss_limit_percent: float = 5.0,
        max_position_size_percent: float = 25.0
    ):
        """
        Инициализация менеджера рисков.
        
        Args:
            max_drawdown_percent: Максимальная просадка в процентах (по умолчанию 20%)
            risk_per_trade_percent: Максимальный риск на сделку в процентах (по умолчанию 2%)
            max_open_positions: Максимальное количество открытых позиций (по умолчанию 5)
            daily_loss_limit_percent: Дневной лимит убытков в процентах (по умолчанию 5%)
            max_position_size_percent: Максимальный размер позиции от баланса (по умолчанию 25%)
        """
        self.max_drawdown = max_drawdown_percent / 100.0
        self.risk_per_trade = risk_per_trade_percent / 100.0
        self.max_positions = max_open_positions
        self.daily_loss_limit = daily_loss_limit_percent / 100.0
        self.max_position_size = max_position_size_percent / 100.0
        
        # Отслеживание состояния
        self.peak_balance = Decimal("0")
        self.daily_start_balance = Decimal("0")
        self.daily_reset_date = None
        self.trading_paused = False
        self.pause_reason = None
    
    def update_peak_balance(self, current_balance: Decimal):
        """
        Обновляет пиковый баланс для расчета просадки.
        
        Args:
            current_balance: Текущий баланс счета
        """
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
    
    def calculate_drawdown(self, current_balance: Decimal) -> float:
        """
        Рассчитывает текущую просадку от пика.
        
        Args:
            current_balance: Текущий баланс
            
        Returns:
            Просадка в процентах (положительное число)
        """
        if self.peak_balance == 0:
            return 0.0
        
        drawdown = (self.peak_balance - current_balance) / self.peak_balance
        return float(drawdown)
    
    def check_max_drawdown(self, current_balance: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, не превышена ли максимальная просадка.
        
        Args:
            current_balance: Текущий баланс
            
        Returns:
            Tuple[можно_торговать, причина_запрета]
        """
        drawdown = self.calculate_drawdown(current_balance)
        
        if drawdown >= self.max_drawdown:
            reason = f"Превышена максимальная просадка: {drawdown*100:.2f}% (лимит {self.max_drawdown*100:.1f}%)"
            return False, reason
        
        return True, None
    
    def reset_daily_tracking(self, current_balance: Decimal):
        """
        Сбрасывает дневное отслеживание убытков.
        
        Args:
            current_balance: Текущий баланс
        """
        today = datetime.now().date()
        if self.daily_reset_date != today:
            self.daily_start_balance = current_balance
            self.daily_reset_date = today
    
    def calculate_daily_pnl(self, current_balance: Decimal) -> float:
        """
        Рассчитывает дневной P&L.
        
        Args:
            current_balance: Текущий баланс
            
        Returns:
            Дневной P&L в процентах
        """
        if self.daily_start_balance == 0:
            return 0.0
        
        daily_pnl = (current_balance - self.daily_start_balance) / self.daily_start_balance
        return float(daily_pnl)
    
    def check_daily_loss_limit(self, current_balance: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, не превышен ли дневной лимит убытков.
        
        Args:
            current_balance: Текущий баланс
            
        Returns:
            Tuple[можно_торговать, причина_запрета]
        """
        self.reset_daily_tracking(current_balance)
        daily_pnl = self.calculate_daily_pnl(current_balance)
        
        if daily_pnl <= -self.daily_loss_limit:
            reason = f"Превышен дневной лимит убытков: {daily_pnl*100:.2f}% (лимит -{self.daily_loss_limit*100:.1f}%)"
            return False, reason
        
        return True, None
    
    def check_position_count(self, current_positions: int) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, не превышено ли максимальное количество позиций.
        
        Args:
            current_positions: Текущее количество открытых позиций
            
        Returns:
            Tuple[можно_открывать, причина_запрета]
        """
        if current_positions >= self.max_positions:
            reason = f"Достигнут лимит открытых позиций: {current_positions} (максимум {self.max_positions})"
            return False, reason
        
        return True, None
    
    def calculate_position_size(
        self,
        balance: Decimal,
        entry_price: Decimal,
        stop_loss: Decimal,
        max_lots: int = None
    ) -> int:
        """
        Рассчитывает размер позиции на основе риска.
        
        Args:
            balance: Доступный баланс
            entry_price: Цена входа
            stop_loss: Уровень стоп-лосса
            max_lots: Максимальное количество лотов (ограничение)
            
        Returns:
            Рекомендуемое количество лотов
        """
        if stop_loss is None or stop_loss == 0:
            # Если нет стоп-лосса, используем консервативный подход
            max_position_value = balance * Decimal(str(self.max_position_size))
            lots = int(max_position_value / entry_price)
        else:
            # Рассчитываем размер на основе риска
            risk_amount = balance * Decimal(str(self.risk_per_trade))
            price_risk = abs(entry_price - stop_loss)
            
            if price_risk > 0:
                lots = int(risk_amount / price_risk)
            else:
                lots = 1
        
        # Ограничиваем размер позиции
        if max_lots is not None:
            lots = min(lots, max_lots)
        
        # Минимум 1 лот
        lots = max(1, lots)
        
        return lots
    
    def validate_position_size(
        self,
        balance: Decimal,
        position_value: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, не превышает ли размер позиции допустимый лимит.
        
        Args:
            balance: Доступный баланс
            position_value: Стоимость позиции
            
        Returns:
            Tuple[допустимый_размер, причина_отказа]
        """
        max_allowed = balance * Decimal(str(self.max_position_size))
        
        if position_value > max_allowed:
            reason = f"Позиция слишком большая: {float(position_value):.2f} ₽ (максимум {float(max_allowed):.2f} ₽)"
            return False, reason
        
        return True, None
    
    def can_open_position(
        self,
        current_balance: Decimal,
        current_positions: int,
        position_value: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """
        Комплексная проверка возможности открытия позиции.
        
        Args:
            current_balance: Текущий баланс
            current_positions: Количество открытых позиций
            position_value: Стоимость новой позиции
            
        Returns:
            Tuple[можно_открывать, причина_запрета]
        """
        # Проверка максимальной просадки
        can_trade, reason = self.check_max_drawdown(current_balance)
        if not can_trade:
            self.trading_paused = True
            self.pause_reason = reason
            return False, reason
        
        # Проверка дневного лимита убытков
        can_trade, reason = self.check_daily_loss_limit(current_balance)
        if not can_trade:
            self.trading_paused = True
            self.pause_reason = reason
            return False, reason
        
        # Проверка количества позиций
        can_open, reason = self.check_position_count(current_positions)
        if not can_open:
            return False, reason
        
        # Проверка размера позиции
        valid_size, reason = self.validate_position_size(current_balance, position_value)
        if not valid_size:
            return False, reason
        
        return True, None
    
    def resume_trading(self):
        """
        Возобновляет торговлю после паузы.
        """
        self.trading_paused = False
        self.pause_reason = None
    
    def get_risk_status(self, current_balance: Decimal, current_positions: int) -> Dict[str, Any]:
        """
        Возвращает текущий статус рисков.
        
        Args:
            current_balance: Текущий баланс
            current_positions: Количество открытых позиций
            
        Returns:
            Словарь со статусом рисков
        """
        self.update_peak_balance(current_balance)
        self.reset_daily_tracking(current_balance)
        
        drawdown = self.calculate_drawdown(current_balance)
        daily_pnl = self.calculate_daily_pnl(current_balance)
        
        return {
            'trading_paused': self.trading_paused,
            'pause_reason': self.pause_reason,
            'peak_balance': float(self.peak_balance),
            'current_balance': float(current_balance),
            'drawdown_percent': drawdown * 100,
            'max_drawdown_percent': self.max_drawdown * 100,
            'daily_pnl_percent': daily_pnl * 100,
            'daily_loss_limit_percent': self.daily_loss_limit * 100,
            'current_positions': current_positions,
            'max_positions': self.max_positions,
            'risk_per_trade_percent': self.risk_per_trade * 100
        }
