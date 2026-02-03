"""
Эндпоинт для работы с ордерами и сделками.
Предоставляет методы для выставления, отмены и получения информации об ордерах.
"""

from typing import List, Optional
from datetime import datetime
from t_tech.invest import OrderDirection as ApiOrderDirection, OrderType as ApiOrderType
from src.models.order import Order, OrderDirection, OrderType, OrderStatus


class OrdersEndpoint:
    """
    Эндпоинт для работы с ордерами через Tinkoff Invest API.
    Позволяет выставлять, отменять и отслеживать торговые заявки.
    """
    
    def __init__(self, services):
        """
        Инициализирует эндпоинт с сервисами API.
        
        Args:
            services: Объект сервисов из AsyncClient
        """
        self._services = services
    
    async def post_market_order(
        self,
        figi: str,
        quantity: int,
        direction: OrderDirection,
        account_id: str
    ) -> Optional[Order]:
        """
        Выставляет рыночный ордер (исполняется по текущей рыночной цене).
        
        Args:
            figi: Уникальный идентификатор инструмента
            quantity: Количество лотов
            direction: Направление (покупка/продажа)
            account_id: ID торгового счета
            
        Returns:
            Модель созданного ордера или None при ошибке
        """
        try:
            api_direction = self._convert_direction_to_api(direction)
            response = await self._services.orders.post_order(
                figi=figi,
                quantity=quantity,
                direction=api_direction,
                account_id=account_id,
                order_type=ApiOrderType.ORDER_TYPE_MARKET
            )
            
            return Order(
                order_id=response.order_id,
                figi=figi,
                direction=direction,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=None,
                status=OrderStatus.PENDING,
                created_at=datetime.now(),
                executed_quantity=response.lots_executed,
                executed_price=self._quotation_to_float(response.executed_order_price) if response.executed_order_price else None
            )
        except Exception as e:
            print(f"Ошибка при выставлении рыночного ордера: {e}")
            return None
    
    async def post_limit_order(
        self,
        figi: str,
        quantity: int,
        price: float,
        direction: OrderDirection,
        account_id: str
    ) -> Optional[Order]:
        """
        Выставляет лимитный ордер (исполняется по указанной цене или лучше).
        
        Args:
            figi: Уникальный идентификатор инструмента
            quantity: Количество лотов
            price: Цена исполнения
            direction: Направление (покупка/продажа)
            account_id: ID торгового счета
            
        Returns:
            Модель созданного ордера или None при ошибке
        """
        try:
            api_direction = self._convert_direction_to_api(direction)
            price_quotation = self._float_to_quotation(price)
            
            response = await self._services.orders.post_order(
                figi=figi,
                quantity=quantity,
                price=price_quotation,
                direction=api_direction,
                account_id=account_id,
                order_type=ApiOrderType.ORDER_TYPE_LIMIT
            )
            
            return Order(
                order_id=response.order_id,
                figi=figi,
                direction=direction,
                order_type=OrderType.LIMIT,
                quantity=quantity,
                price=price,
                status=OrderStatus.PENDING,
                created_at=datetime.now(),
                executed_quantity=response.lots_executed,
                executed_price=self._quotation_to_float(response.executed_order_price) if response.executed_order_price else None
            )
        except Exception as e:
            print(f"Ошибка при выставлении лимитного ордера: {e}")
            return None
    
    async def cancel_order(self, order_id: str, account_id: str) -> bool:
        """
        Отменяет активный ордер.
        
        Args:
            order_id: ID ордера для отмены
            account_id: ID торгового счета
            
        Returns:
            True если отмена успешна, False при ошибке
        """
        try:
            await self._services.orders.cancel_order(
                account_id=account_id,
                order_id=order_id
            )
            return True
        except Exception as e:
            print(f"Ошибка при отмене ордера: {e}")
            return False
    
    async def get_orders(self, account_id: str) -> List[Order]:
        """
        Получает список активных ордеров.
        
        Args:
            account_id: ID торгового счета
            
        Returns:
            Список моделей активных ордеров
        """
        try:
            response = await self._services.orders.get_orders(account_id=account_id)
            return [self._convert_api_order_to_model(order) for order in response.orders]
        except Exception as e:
            print(f"Ошибка при получении списка ордеров: {e}")
            return []
    
    async def get_order_state(self, order_id: str, account_id: str) -> Optional[Order]:
        """
        Получает состояние конкретного ордера.
        
        Args:
            order_id: ID ордера
            account_id: ID торгового счета
            
        Returns:
            Модель ордера или None при ошибке
        """
        try:
            response = await self._services.orders.get_order_state(
                account_id=account_id,
                order_id=order_id
            )
            return self._convert_api_order_to_model(response)
        except Exception as e:
            print(f"Ошибка при получении состояния ордера: {e}")
            return None
    
    def _convert_api_order_to_model(self, api_order) -> Order:
        """
        Конвертирует ордер из API в модель Order.
        
        Args:
            api_order: Объект ордера из API
            
        Returns:
            Модель ордера
        """
        direction = OrderDirection.BUY if api_order.direction == ApiOrderDirection.ORDER_DIRECTION_BUY else OrderDirection.SELL
        order_type = OrderType.MARKET if api_order.order_type == ApiOrderType.ORDER_TYPE_MARKET else OrderType.LIMIT
        
        status_map = {
            1: OrderStatus.PENDING,
            2: OrderStatus.FILLED,
            3: OrderStatus.CANCELLED,
            4: OrderStatus.REJECTED,
            5: OrderStatus.PARTIALLY_FILLED
        }
        status = status_map.get(api_order.execution_report_status, OrderStatus.PENDING)
        
        return Order(
            order_id=api_order.order_id,
            figi=api_order.figi,
            direction=direction,
            order_type=order_type,
            quantity=api_order.lots_requested,
            price=self._quotation_to_float(api_order.initial_order_price) if hasattr(api_order, 'initial_order_price') else None,
            status=status,
            created_at=api_order.order_date if hasattr(api_order, 'order_date') else datetime.now(),
            executed_quantity=api_order.lots_executed,
            executed_price=self._quotation_to_float(api_order.executed_order_price) if hasattr(api_order, 'executed_order_price') else None
        )
    
    @staticmethod
    def _convert_direction_to_api(direction: OrderDirection) -> ApiOrderDirection:
        """
        Конвертирует направление ордера в формат API.
        
        Args:
            direction: Направление из модели
            
        Returns:
            Направление для API
        """
        return ApiOrderDirection.ORDER_DIRECTION_BUY if direction == OrderDirection.BUY else ApiOrderDirection.ORDER_DIRECTION_SELL
    
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
    
    @staticmethod
    def _float_to_quotation(value: float):
        """
        Конвертирует float в Quotation для API.
        
        Args:
            value: Число с плавающей точкой
            
        Returns:
            Объект Quotation
        """
        from t_tech.invest import Quotation
        units = int(value)
        nano = int((value - units) * 1e9)
        return Quotation(units=units, nano=nano)
