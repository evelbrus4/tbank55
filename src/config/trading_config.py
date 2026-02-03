"""
Конфигурационный файл для настройки параметров торгового бота.
Все параметры реалистичности и риск-менеджмента настраиваются здесь.
"""

from typing import Dict, Any


class TradingConfig:
    """
    Класс с конфигурацией торгового бота.
    Содержит настройки для всех компонентов системы.
    """
    
    # ==================== ПРОСКАЛЬЗЫВАНИЕ (SLIPPAGE) ====================
    SLIPPAGE_CONFIG: Dict[str, Any] = {
        'enabled': True,  # Включить/выключить проскальзывание
        'base_slippage_percent': 0.02,  # Базовое проскальзывание 0.02%
        'volume_factor_per_10_lots': 0.01,  # +0.01% за каждые 10 лотов
        'volatility_multiplier': 2.0,  # Множитель волатильности
        'max_slippage_percent': 0.5  # Максимальное проскальзывание 0.5%
    }
    
    # ==================== СПРЕД BID/ASK ====================
    SPREAD_CONFIG: Dict[str, Any] = {
        'enabled': True,  # Включить/выключить спред
        'base_spread_percent': 0.03,  # Базовый спред 0.03%
        'volatility_multiplier': 1.5,  # Множитель волатильности
        'min_spread_percent': 0.01,  # Минимальный спред 0.01%
        'max_spread_percent': 0.1  # Максимальный спред 0.1%
    }
    
    # ==================== ЗАДЕРЖКА ИСПОЛНЕНИЯ ОРДЕРОВ ====================
    ORDER_EXECUTION_CONFIG: Dict[str, Any] = {
        'enabled': True,  # Включить/выключить задержку
        'min_delay_seconds': 1.0,  # Минимальная задержка 1 сек
        'max_delay_seconds': 3.0,  # Максимальная задержка 3 сек
        'max_price_deviation_percent': 1.0  # Максимальное отклонение цены для отмены 1%
    }
    
    # ==================== РИСК-МЕНЕДЖМЕНТ ====================
    RISK_CONFIG: Dict[str, Any] = {
        'enabled': True,  # Включить/выключить риск-менеджмент
        'max_drawdown_percent': 20.0,  # Максимальная просадка 20%
        'risk_per_trade_percent': 2.0,  # Риск на сделку 2%
        'max_open_positions': 5,  # Максимум 5 открытых позиций
        'daily_loss_limit_percent': 5.0,  # Дневной лимит убытков 5%
        'max_position_size_percent': 25.0  # Максимальный размер позиции 25% от баланса
    }
    
    # ==================== МЕТРИКИ ПРОИЗВОДИТЕЛЬНОСТИ ====================
    METRICS_CONFIG: Dict[str, Any] = {
        'enabled': True,  # Включить/выключить расчет метрик
        'risk_free_rate': 0.0,  # Безрисковая ставка 0%
        'calculate_on_close': True,  # Рассчитывать метрики при закрытии позиции
        'log_metrics': True  # Логировать метрики
    }
    
    # ==================== ОБЩИЕ НАСТРОЙКИ ====================
    GENERAL_CONFIG: Dict[str, Any] = {
        'initial_balance': 200000.0,  # Начальный баланс 200,000 ₽
        'commission_rate': 0.0005,  # Комиссия 0.05%
        'use_realistic_execution': True,  # Использовать реалистичное исполнение
        'log_level': 'INFO'  # Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    }
    
    # ==================== НАСТРОЙКИ СТРАТЕГИИ ====================
    STRATEGY_CONFIG: Dict[str, Any] = {
        'max_lots_per_instrument': 100,  # Максимум 100 лотов на инструмент
        'min_lots': 1,  # Минимум 1 лот
        'atr_stop_loss_multiplier': 2.0,  # SL = 2 * ATR
        'atr_take_profit_multiplier': 3.0,  # TP = 3 * ATR
        'position_sizing_method': 'risk_based'  # 'risk_based' или 'fixed'
    }
    
    @classmethod
    def get_config(cls, config_name: str) -> Dict[str, Any]:
        """
        Получает конфигурацию по имени.
        
        Args:
            config_name: Имя конфигурации (например, 'SLIPPAGE_CONFIG')
            
        Returns:
            Словарь с конфигурацией
        """
        return getattr(cls, config_name, {})
    
    @classmethod
    def is_enabled(cls, feature: str) -> bool:
        """
        Проверяет, включена ли функция.
        
        Args:
            feature: Название функции ('slippage', 'spread', 'order_execution', 'risk', 'metrics')
            
        Returns:
            True если функция включена
        """
        config_map = {
            'slippage': 'SLIPPAGE_CONFIG',
            'spread': 'SPREAD_CONFIG',
            'order_execution': 'ORDER_EXECUTION_CONFIG',
            'risk': 'RISK_CONFIG',
            'metrics': 'METRICS_CONFIG'
        }
        
        config_name = config_map.get(feature)
        if not config_name:
            return False
        
        config = cls.get_config(config_name)
        return config.get('enabled', False)
    
    @classmethod
    def get_all_configs(cls) -> Dict[str, Dict[str, Any]]:
        """
        Возвращает все конфигурации.
        
        Returns:
            Словарь со всеми конфигурациями
        """
        return {
            'slippage': cls.SLIPPAGE_CONFIG,
            'spread': cls.SPREAD_CONFIG,
            'order_execution': cls.ORDER_EXECUTION_CONFIG,
            'risk': cls.RISK_CONFIG,
            'metrics': cls.METRICS_CONFIG,
            'general': cls.GENERAL_CONFIG,
            'strategy': cls.STRATEGY_CONFIG
        }


# ==================== ПРЕСЕТЫ КОНФИГУРАЦИЙ ====================

class ConservativeConfig(TradingConfig):
    """
    Консервативная конфигурация с повышенными требованиями к риск-менеджменту.
    """
    RISK_CONFIG = {
        'enabled': True,
        'max_drawdown_percent': 100.0,  #  Более строгий лимит просадки
        'risk_per_trade_percent': 100.0,  #  Меньший риск на сделку
        'max_open_positions': 100,  #  Меньше позиций
        'daily_loss_limit_percent': 100.0,  #  Более строгий дневной лимит
        'max_position_size_percent': 100.0,  #  Меньший размер позиции
    }


class AggressiveConfig(TradingConfig):
    """
    Агрессивная конфигурация с большими рисками и потенциально большей доходностью.
    """
    RISK_CONFIG = {
        'enabled': True,
        'max_drawdown_percent': 100.0,  #  Больший лимит просадки
        'risk_per_trade_percent': 100.0,  #  Больший риск на сделку
        'max_open_positions': 100,  #  Больше позиций
        'daily_loss_limit_percent': 100.0,  #  Более мягкий дневной лимит
        'max_position_size_percent': 100.0,  #  Больший размер позиции
    }


class TestingConfig(TradingConfig):
    """
    Конфигурация для тестирования без реалистичных ограничений.
    """
    SLIPPAGE_CONFIG = {
        'enabled': False,  #  Отключено
        'base_slippage_percent': 0.0,
        'volume_factor_per_10_lots': 0.0,
        'volatility_multiplier': 0.0,
        'max_slippage_percent': 0.0
    }
    
    SPREAD_CONFIG = {
        'enabled': False,  #  Отключено
        'base_spread_percent': 0.0,
        'volatility_multiplier': 0.0,
        'min_spread_percent': 0.0,
        'max_spread_percent': 0.0
    }
    
    ORDER_EXECUTION_CONFIG = {
        'enabled': False,  #  Отключено
        'min_delay_seconds': 0.0,
        'max_delay_seconds': 0.0,
        'max_price_deviation_percent': 100.0
    }
    
    RISK_CONFIG = {
        'enabled': False,  #  Отключено
        'max_drawdown_percent': 100.0,
        'risk_per_trade_percent': 100.0,
        'max_open_positions': 100,
        'daily_loss_limit_percent': 100.0,
        'max_position_size_percent': 100.0
    }


# Выбор активной конфигурации
ACTIVE_CONFIG = TradingConfig  # Можно изменить на ConservativeConfig, AggressiveConfig или TestingConfig
