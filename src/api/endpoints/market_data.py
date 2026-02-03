"""
Эндпоинт для работы с рыночными данными.
Предоставляет методы для получения свечей, стаканов, последних цен и других рыночных данных.
"""

from typing import List, AsyncGenerator
from datetime import datetime
from t_tech.invest import CandleInterval
from src.models.candle import Candle


class MarketDataEndpoint:
    """
    Эндпоинт для работы с рыночными данными через Tinkoff Invest API.
    Позволяет получать исторические и текущие данные о ценах и объемах.
    """
    
    def __init__(self, services):
        """
        Инициализирует эндпоинт с сервисами API.
        
        Args:
            services: Объект сервисов из AsyncClient
        """
        self._services = services
    
    async def get_candles(
        self,
        figi: str,
        from_date: datetime,
        to_date: datetime,
        interval: CandleInterval
    ) -> AsyncGenerator[Candle, None]:
        """
        Получает исторические свечи для инструмента.
        Возвращает генератор для обработки больших объемов данных.
        
        Args:
            figi: Уникальный идентификатор инструмента
            from_date: Начальная дата периода
            to_date: Конечная дата периода
            interval: Интервал свечей (1min, 5min, hour, day и т.д.)
            
        Yields:
            Модели свечей
        """
        async for candle in self._services.get_all_candles(
            figi=figi,
            from_=from_date,
            to=to_date,
            interval=interval
        ):
            yield self._convert_to_candle_model(candle, figi, interval)
    
    async def get_candles_list(
        self,
        figi: str,
        from_date: datetime,
        to_date: datetime,
        interval: CandleInterval
    ) -> List[Candle]:
        """
        Получает список всех свечей для инструмента.
        Использует get_candles и собирает все результаты в список.
        
        Args:
            figi: Уникальный идентификатор инструмента
            from_date: Начальная дата периода
            to_date: Конечная дата периода
            interval: Интервал свечей
            
        Returns:
            Список моделей свечей
        """
        candles = []
        async for candle in self.get_candles(figi, from_date, to_date, interval):
            candles.append(candle)
        return candles
    
    async def get_last_prices(self, figis: List[str]) -> dict:
        """
        Получает последние цены для списка инструментов.
        
        Args:
            figis: Список FIGI инструментов
            
        Returns:
            Словарь {figi: цена}
        """
        try:
            response = await self._services.market_data.get_last_prices(figi=figis)
            return {
                price.figi: self._quotation_to_float(price.price)
                for price in response.last_prices
            }
        except Exception:
            return {}
    
    async def get_last_price(self, figi: str) -> float:
        """
        Получает последнюю цену для одного инструмента.
        
        Args:
            figi: Уникальный идентификатор инструмента
            
        Returns:
            Последняя цена или 0.0 при ошибке
        """
        prices = await self.get_last_prices([figi])
        return prices.get(figi, 0.0)
    
    async def get_order_book(self, figi: str, depth: int = 10) -> dict:
        """
        Получает стакан заявок для инструмента.
        
        Args:
            figi: Уникальный идентификатор инструмента
            depth: Глубина стакана (количество уровней)
            
        Returns:
            Словарь с данными стакана (bids, asks)
        """
        try:
            response = await self._services.market_data.get_order_book(
                figi=figi,
                depth=depth
            )
            return {
                'figi': figi,
                'depth': depth,
                'bids': [
                    {'price': self._quotation_to_float(bid.price), 'quantity': bid.quantity}
                    for bid in response.bids
                ],
                'asks': [
                    {'price': self._quotation_to_float(ask.price), 'quantity': ask.quantity}
                    for ask in response.asks
                ],
                'last_price': self._quotation_to_float(response.last_price) if response.last_price else None
            }
        except Exception:
            return {'figi': figi, 'bids': [], 'asks': [], 'last_price': None}
    
    async def get_trading_status(self, figi: str) -> dict:
        """
        Получает статус торгов для инструмента.
        
        Args:
            figi: Уникальный идентификатор инструмента
            
        Returns:
            Словарь со статусом торгов
        """
        try:
            response = await self._services.market_data.get_trading_status(figi=figi)
            return {
                'figi': figi,
                'trading_status': response.trading_status,
                'limit_order_available': response.limit_order_available_flag,
                'market_order_available': response.market_order_available_flag,
                'api_trade_available': response.api_trade_available_flag
            }
        except Exception:
            return {'figi': figi, 'trading_status': None}
    
    def _convert_to_candle_model(self, candle, figi: str, interval: CandleInterval) -> Candle:
        """
        Конвертирует свечу из API в модель Candle.
        
        Args:
            candle: Объект свечи из API
            figi: FIGI инструмента
            interval: Интервал свечи
            
        Returns:
            Модель свечи
        """
        return Candle(
            time=candle.time,
            open=self._quotation_to_float(candle.open),
            high=self._quotation_to_float(candle.high),
            low=self._quotation_to_float(candle.low),
            close=self._quotation_to_float(candle.close),
            volume=candle.volume,
            figi=figi,
            interval=str(interval),
            is_complete=candle.is_complete
        )
    
    @staticmethod
    def _quotation_to_float(quotation) -> float:
        """
        Конвертирует Quotation из API в float.
        
        Args:
            quotation: Объект Quotation с units и nano
            
        Returns:
            Число с плавающей точкой
        """
        if quotation is None:
            return 0.0
        return float(quotation.units) + float(quotation.nano) / 1e9
