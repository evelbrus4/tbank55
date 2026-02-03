"""
Модуль для расчета метрик производительности торговой стратегии.
Включает расчет Sharpe Ratio, Maximum Drawdown, Profit Factor и других метрик.
"""

import numpy as np
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class PerformanceMetrics:
    """
    Класс для расчета метрик производительности торговой стратегии.
    
    Рассчитываемые метрики:
    - Sharpe Ratio - доходность с учетом риска
    - Maximum Drawdown - максимальная просадка
    - Profit Factor - отношение прибыльных к убыточным
    - Win Rate - процент прибыльных сделок
    - Average Trade Duration - средняя длительность сделки
    - Expectancy - математическое ожидание прибыли
    - Recovery Factor - способность восстановления
    """
    
    def __init__(self, risk_free_rate: float = 0.0):
        """
        Инициализация калькулятора метрик.
        
        Args:
            risk_free_rate: Безрисковая ставка доходности (годовая, по умолчанию 0%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 252
    ) -> float:
        """
        Рассчитывает Sharpe Ratio - показатель доходности с учетом риска.
        
        Args:
            returns: Список доходностей (в долях, например 0.02 = 2%)
            periods_per_year: Количество периодов в году (252 для дневных данных)
            
        Returns:
            Sharpe Ratio (чем выше, тем лучше)
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        # Аннуализированный Sharpe Ratio
        sharpe = (mean_return - self.risk_free_rate / periods_per_year) / std_return
        sharpe_annual = sharpe * np.sqrt(periods_per_year)
        
        return float(sharpe_annual)
    
    def calculate_max_drawdown(self, balance_history: List[float]) -> Dict[str, Any]:
        """
        Рассчитывает максимальную просадку.
        
        Args:
            balance_history: История баланса счета
            
        Returns:
            Словарь с информацией о максимальной просадке
        """
        if not balance_history or len(balance_history) < 2:
            return {
                'max_drawdown_percent': 0.0,
                'max_drawdown_value': 0.0,
                'peak_value': 0.0,
                'trough_value': 0.0
            }
        
        balance_array = np.array(balance_history)
        peak = balance_array[0]
        max_dd = 0.0
        max_dd_value = 0.0
        peak_value = peak
        trough_value = peak
        
        for value in balance_array:
            if value > peak:
                peak = value
            
            dd = (peak - value) / peak if peak > 0 else 0
            
            if dd > max_dd:
                max_dd = dd
                max_dd_value = peak - value
                peak_value = peak
                trough_value = value
        
        return {
            'max_drawdown_percent': float(max_dd * 100),
            'max_drawdown_value': float(max_dd_value),
            'peak_value': float(peak_value),
            'trough_value': float(trough_value)
        }
    
    def calculate_profit_factor(self, trades: List[Dict[str, Any]]) -> float:
        """
        Рассчитывает Profit Factor - отношение прибыльных сделок к убыточным.
        
        Args:
            trades: Список сделок с полем 'net_profit'
            
        Returns:
            Profit Factor (>1 хорошо, <1 плохо)
        """
        if not trades:
            return 0.0
        
        gross_profit = sum(float(t.get('net_profit', 0)) for t in trades if float(t.get('net_profit', 0)) > 0)
        gross_loss = abs(sum(float(t.get('net_profit', 0)) for t in trades if float(t.get('net_profit', 0)) < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def calculate_win_rate(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Рассчитывает процент прибыльных сделок.
        
        Args:
            trades: Список сделок с полем 'net_profit'
            
        Returns:
            Словарь с информацией о win rate
        """
        if not trades:
            return {
                'win_rate_percent': 0.0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_trades': 0
            }
        
        winning_trades = sum(1 for t in trades if float(t.get('net_profit', 0)) > 0)
        losing_trades = sum(1 for t in trades if float(t.get('net_profit', 0)) < 0)
        total_trades = len(trades)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        return {
            'win_rate_percent': float(win_rate),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_trades': total_trades
        }
    
    def calculate_average_trade_duration(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Рассчитывает среднюю длительность сделки.
        
        Args:
            trades: Список сделок с полями 'opened_at' и 'timestamp' (закрытия)
            
        Returns:
            Словарь с информацией о длительности сделок
        """
        if not trades:
            return {
                'avg_duration_minutes': 0.0,
                'avg_duration_hours': 0.0,
                'min_duration_minutes': 0.0,
                'max_duration_minutes': 0.0
            }
        
        durations = []
        for trade in trades:
            if 'opened_at' in trade and 'timestamp' in trade:
                try:
                    opened = datetime.strptime(trade['opened_at'], '%Y-%m-%d %H:%M:%S')
                    closed = datetime.strptime(trade['timestamp'], '%Y-%m-%d %H:%M:%S')
                    duration = (closed - opened).total_seconds() / 60  # в минутах
                    durations.append(duration)
                except:
                    continue
        
        if not durations:
            return {
                'avg_duration_minutes': 0.0,
                'avg_duration_hours': 0.0,
                'min_duration_minutes': 0.0,
                'max_duration_minutes': 0.0
            }
        
        avg_duration = np.mean(durations)
        min_duration = np.min(durations)
        max_duration = np.max(durations)
        
        return {
            'avg_duration_minutes': float(avg_duration),
            'avg_duration_hours': float(avg_duration / 60),
            'min_duration_minutes': float(min_duration),
            'max_duration_minutes': float(max_duration)
        }
    
    def calculate_expectancy(self, trades: List[Dict[str, Any]]) -> float:
        """
        Рассчитывает математическое ожидание прибыли на сделку.
        
        Args:
            trades: Список сделок с полем 'net_profit'
            
        Returns:
            Expectancy (средняя прибыль на сделку)
        """
        if not trades:
            return 0.0
        
        win_rate_info = self.calculate_win_rate(trades)
        win_rate = win_rate_info['win_rate_percent'] / 100
        
        winning_trades = [float(t.get('net_profit', 0)) for t in trades if float(t.get('net_profit', 0)) > 0]
        losing_trades = [float(t.get('net_profit', 0)) for t in trades if float(t.get('net_profit', 0)) < 0]
        
        avg_win = np.mean(winning_trades) if winning_trades else 0.0
        avg_loss = abs(np.mean(losing_trades)) if losing_trades else 0.0
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        return float(expectancy)
    
    def calculate_recovery_factor(
        self,
        net_profit: float,
        max_drawdown: float
    ) -> float:
        """
        Рассчитывает Recovery Factor - способность восстановления после просадки.
        
        Args:
            net_profit: Чистая прибыль
            max_drawdown: Максимальная просадка (в абсолютных единицах)
            
        Returns:
            Recovery Factor (чем выше, тем лучше)
        """
        if max_drawdown == 0:
            return float('inf') if net_profit > 0 else 0.0
        
        return net_profit / max_drawdown
    
    def calculate_all_metrics(
        self,
        balance_history: List[float],
        trades: List[Dict[str, Any]],
        initial_balance: float
    ) -> Dict[str, Any]:
        """
        Рассчитывает все метрики производительности.
        
        Args:
            balance_history: История баланса
            trades: Список закрытых сделок
            initial_balance: Начальный баланс
            
        Returns:
            Словарь со всеми метриками
        """
        # Фильтруем только закрытые сделки
        closed_trades = [t for t in trades if t.get('action') == 'close']
        
        # Рассчитываем доходности
        returns = []
        if len(balance_history) > 1:
            for i in range(1, len(balance_history)):
                ret = (balance_history[i] - balance_history[i-1]) / balance_history[i-1]
                returns.append(ret)
        
        # Рассчитываем метрики
        sharpe = self.calculate_sharpe_ratio(returns)
        max_dd = self.calculate_max_drawdown(balance_history)
        profit_factor = self.calculate_profit_factor(closed_trades)
        win_rate = self.calculate_win_rate(closed_trades)
        avg_duration = self.calculate_average_trade_duration(closed_trades)
        expectancy = self.calculate_expectancy(closed_trades)
        
        current_balance = balance_history[-1] if balance_history else initial_balance
        net_profit = current_balance - initial_balance
        recovery_factor = self.calculate_recovery_factor(net_profit, max_dd['max_drawdown_value'])
        
        # Дополнительные метрики
        total_return = ((current_balance - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0.0
        
        return {
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'avg_trade_duration': avg_duration,
            'expectancy': expectancy,
            'recovery_factor': recovery_factor,
            'total_return_percent': float(total_return),
            'net_profit': float(net_profit),
            'initial_balance': float(initial_balance),
            'current_balance': float(current_balance),
            'total_trades': len(closed_trades)
        }
