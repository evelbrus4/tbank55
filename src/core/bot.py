import os
import asyncio
from typing import List, Dict, Optional, AsyncGenerator
from datetime import datetime
from t_tech.invest import CandleInterval

from src.api.tinkoff_client import TinkoffClient
from src.models.instrument import Instrument
from src.models.candle import Candle
from src.models.order import Order, OrderDirection
from src.models.portfolio import Portfolio, Position


class TInvestBot:
    """
    Основной класс бота для взаимодействия с T-Invest API.
    Использует новую архитектуру с разделением на API клиент, эндпоинты и модели данных.
    Обеспечивает высокоуровневый интерфейс для торговых операций.
    """
    
    def __init__(self, token: str):
        """
        Инициализирует бота с токеном доступа к API.
        
        Args:
            token: Токен для доступа к Тинькофф Инвестиций API
        """
        self.token = token
        self.client: Optional[TinkoffClient] = None
        self.account_id: Optional[str] = None

    async def __aenter__(self):
        """
        Асинхронный вход в контекст - устанавливает соединение с API.
        Инициализирует клиент и все эндпоинты.
        """
        self.client = TinkoffClient(self.token)
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Асинхронный выход из контекста - закрывает соединение с API.
        """
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def get_russian_shares(self) -> List[Instrument]:
        """
        Получает список российских акций, доступных для торговли.
        Использует эндпоинт instruments для получения данных.
        
        Returns:
            Список моделей российских акций
        """
        return await self.client.instruments.get_russian_shares()
    
    async def get_share_by_ticker(self, ticker: str) -> Optional[Instrument]:
        """
        Получает информацию об акции по тикеру.
        
        Args:
            ticker: Тикер акции (например, "SBER")
            
        Returns:
            Модель инструмента или None
        """
        return await self.client.instruments.get_share_by_ticker(ticker)
    
    async def get_share_by_figi(self, figi: str) -> Optional[Instrument]:
        """
        Получает информацию об акции по FIGI.
        
        Args:
            figi: Уникальный идентификатор инструмента
            
        Returns:
            Модель инструмента или None
        """
        return await self.client.instruments.get_share_by_figi(figi)

    async def get_candles(
        self, 
        figi: str, 
        from_date: datetime, 
        to_date: datetime, 
        interval: CandleInterval
    ) -> AsyncGenerator[Candle, None]:
        """
        Загружает свечи для указанного инструмента.
        Возвращает генератор для эффективной обработки больших объемов данных.
        
        Args:
            figi: Уникальный идентификатор инструмента
            from_date: Начальная дата периода
            to_date: Конечная дата периода
            interval: Интервал свечей
            
        Yields:
            Модели свечей
        """
        async for candle in self.client.market_data.get_candles(figi, from_date, to_date, interval):
            yield candle
    
    async def get_candles_list(
        self,
        figi: str,
        from_date: datetime,
        to_date: datetime,
        interval: CandleInterval
    ) -> List[Candle]:
        """
        Загружает все свечи для инструмента в виде списка.
        
        Args:
            figi: Уникальный идентификатор инструмента
            from_date: Начальная дата периода
            to_date: Конечная дата периода
            interval: Интервал свечей
            
        Returns:
            Список моделей свечей
        """
        return await self.client.market_data.get_candles_list(figi, from_date, to_date, interval)
    
    async def get_last_price(self, figi: str) -> float:
        """
        Получает последнюю цену инструмента.
        
        Args:
            figi: Уникальный идентификатор инструмента
            
        Returns:
            Последняя цена
        """
        return await self.client.market_data.get_last_price(figi)
    
    async def get_last_prices(self, figis: List[str]) -> Dict[str, float]:
        """
        Получает последние цены для нескольких инструментов.
        
        Args:
            figis: Список FIGI инструментов
            
        Returns:
            Словарь {figi: цена}
        """
        return await self.client.market_data.get_last_prices(figis)
    
    async def get_order_book(self, figi: str, depth: int = 10) -> dict:
        """
        Получает стакан заявок для инструмента.
        
        Args:
            figi: Уникальный идентификатор инструмента
            depth: Глубина стакана
            
        Returns:
            Словарь с данными стакана
        """
        return await self.client.market_data.get_order_book(figi, depth)
    
    async def get_future_info(self, figi: str) -> Optional[dict]:
        """
        Получает информацию о фьючерсе, включая коэффициенты плеч.
        
        Args:
            figi: Уникальный идентификатор фьючерса
            
        Returns:
            Информация о фьючерсе
        """
        return await self.client.instruments.get_future_by_figi(figi)
    
    async def buy_market(self, figi: str, quantity: int) -> Optional[Order]:
        """
        Выставляет рыночный ордер на покупку.
        
        Args:
            figi: Уникальный идентификатор инструмента
            quantity: Количество лотов
            
        Returns:
            Модель созданного ордера или None
        """
        if not self.account_id:
            raise ValueError("Account ID не установлен. Используйте set_account_id()")
        return await self.client.orders.post_market_order(
            figi=figi,
            quantity=quantity,
            direction=OrderDirection.BUY,
            account_id=self.account_id
        )
    
    async def sell_market(self, figi: str, quantity: int) -> Optional[Order]:
        """
        Выставляет рыночный ордер на продажу.
        
        Args:
            figi: Уникальный идентификатор инструмента
            quantity: Количество лотов
            
        Returns:
            Модель созданного ордера или None
        """
        if not self.account_id:
            raise ValueError("Account ID не установлен. Используйте set_account_id()")
        return await self.client.orders.post_market_order(
            figi=figi,
            quantity=quantity,
            direction=OrderDirection.SELL,
            account_id=self.account_id
        )
    
    async def buy_limit(self, figi: str, quantity: int, price: float) -> Optional[Order]:
        """
        Выставляет лимитный ордер на покупку.
        
        Args:
            figi: Уникальный идентификатор инструмента
            quantity: Количество лотов
            price: Цена исполнения
            
        Returns:
            Модель созданного ордера или None
        """
        if not self.account_id:
            raise ValueError("Account ID не установлен. Используйте set_account_id()")
        return await self.client.orders.post_limit_order(
            figi=figi,
            quantity=quantity,
            price=price,
            direction=OrderDirection.BUY,
            account_id=self.account_id
        )
    
    async def sell_limit(self, figi: str, quantity: int, price: float) -> Optional[Order]:
        """
        Выставляет лимитный ордер на продажу.
        
        Args:
            figi: Уникальный идентификатор инструмента
            quantity: Количество лотов
            price: Цена исполнения
            
        Returns:
            Модель созданного ордера или None
        """
        if not self.account_id:
            raise ValueError("Account ID не установлен. Используйте set_account_id()")
        return await self.client.orders.post_limit_order(
            figi=figi,
            quantity=quantity,
            price=price,
            direction=OrderDirection.SELL,
            account_id=self.account_id
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Отменяет активный ордер.
        
        Args:
            order_id: ID ордера для отмены
            
        Returns:
            True если отмена успешна
        """
        if not self.account_id:
            raise ValueError("Account ID не установлен. Используйте set_account_id()")
        return await self.client.orders.cancel_order(order_id, self.account_id)
    
    async def get_active_orders(self) -> List[Order]:
        """
        Получает список активных ордеров.
        
        Returns:
            Список моделей активных ордеров
        """
        if not self.account_id:
            raise ValueError("Account ID не установлен. Используйте set_account_id()")
        return await self.client.orders.get_orders(self.account_id)
    
    async def get_order_state(self, order_id: str) -> Optional[Order]:
        """
        Получает состояние конкретного ордера.
        
        Args:
            order_id: ID ордера
            
        Returns:
            Модель ордера или None
        """
        if not self.account_id:
            raise ValueError("Account ID не установлен. Используйте set_account_id()")
        return await self.client.orders.get_order_state(order_id, self.account_id)
    
    def set_account_id(self, account_id: str) -> None:
        """
        Устанавливает ID торгового счета для операций с ордерами.
        
        Args:
            account_id: ID торгового счета
        """
        self.account_id = account_id
