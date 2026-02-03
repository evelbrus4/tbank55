"""
Эндпоинт для работы с торговыми инструментами.
Предоставляет методы для получения информации об акциях, фьючерсах и других инструментах.
"""

from typing import List, Optional
from t_tech.invest import InstrumentStatus, Share, Future
from src.models.instrument import Instrument


class InstrumentsEndpoint:
    """
    Эндпоинт для работы с инструментами через Tinkoff Invest API.
    Позволяет получать информацию об акциях, фьючерсах и других торговых инструментах.
    """
    
    def __init__(self, services):
        """
        Инициализирует эндпоинт с сервисами API.
        
        Args:
            services: Объект сервисов из AsyncClient
        """
        self._services = services
    
    async def get_shares(
        self, 
        status: InstrumentStatus = InstrumentStatus.INSTRUMENT_STATUS_BASE
    ) -> List[Share]:
        """
        Получает список всех акций.
        
        Args:
            status: Статус инструментов для фильтрации
            
        Returns:
            Список акций из API
        """
        response = await self._services.instruments.shares(instrument_status=status)
        return response.instruments
    
    async def get_russian_shares(self) -> List[Instrument]:
        """
        Получает список российских акций, доступных для торговли.
        Фильтрует только те акции, которые можно торговать через API.
        
        Returns:
            Список моделей российских акций
        """
        shares = await self.get_shares()
        russian_shares = [
            s for s in shares 
            if s.country_of_risk == "RU" and s.api_trade_available_flag
        ]
        
        return [self._convert_share_to_instrument(share) for share in russian_shares]
    
    async def get_share_by_figi(self, figi: str) -> Optional[Instrument]:
        """
        Получает информацию об акции по FIGI.
        
        Args:
            figi: Уникальный идентификатор инструмента
            
        Returns:
            Модель инструмента или None, если не найден
        """
        try:
            response = await self._services.instruments.share_by(
                id_type=1,  # FIGI
                id=figi
            )
            return self._convert_share_to_instrument(response.instrument)
        except Exception:
            return None
    
    async def get_share_by_ticker(self, ticker: str) -> Optional[Instrument]:
        """
        Получает информацию об акции по тикеру.
        
        Args:
            ticker: Тикер инструмента (например, "SBER")
            
        Returns:
            Модель инструмента или None, если не найден
        """
        shares = await self.get_shares()
        for share in shares:
            if share.ticker == ticker:
                return self._convert_share_to_instrument(share)
        return None
    
    async def get_future_by_figi(self, figi: str) -> Optional[dict]:
        """
        Получает информацию о фьючерсе по FIGI.
        Включает данные о коэффициентах плеч и других параметрах.
        
        Args:
            figi: Уникальный идентификатор фьючерса
            
        Returns:
            Информация о фьючерсе
        """
        try:
            response = await self._services.instruments.future_by(
                id_type=1,  # FIGI
                id=figi
            )
            return response.instrument
        except Exception:
            return None
    
    async def get_futures(
        self, 
        status: InstrumentStatus = InstrumentStatus.INSTRUMENT_STATUS_BASE
    ) -> List[Future]:
        """
        Получает список всех фьючерсов.
        
        Args:
            status: Статус инструментов для фильтрации
            
        Returns:
            Список фьючерсов из API
        """
        response = await self._services.instruments.futures(instrument_status=status)
        return response.instruments
    
    def _convert_share_to_instrument(self, share: Share) -> Instrument:
        """
        Конвертирует объект Share из API в модель Instrument.
        
        Args:
            share: Объект акции из API
            
        Returns:
            Модель инструмента
        """
        return Instrument(
            figi=share.figi,
            ticker=share.ticker,
            name=share.name,
            lot=share.lot,
            currency=share.currency,
            country_of_risk=share.country_of_risk,
            exchange=share.exchange,
            instrument_type="share",
            api_trade_available=share.api_trade_available_flag,
            min_price_increment=self._quotation_to_float(share.min_price_increment),
            short_enabled=share.short_enabled_flag
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
        return float(quotation.units) + float(quotation.nano) / 1e9
