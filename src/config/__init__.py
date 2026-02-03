"""
Конфигурационные файлы для торгового бота.
Содержит настройки для всех компонентов системы.
"""

from .trading_config import (
    TradingConfig,
    ConservativeConfig,
    AggressiveConfig,
    TestingConfig,
    ACTIVE_CONFIG
)

__all__ = [
    'TradingConfig',
    'ConservativeConfig',
    'AggressiveConfig',
    'TestingConfig',
    'ACTIVE_CONFIG'
]
