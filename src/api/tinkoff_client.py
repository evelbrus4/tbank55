"""
Клиент для работы с API Тинькофф Инвестиций.
Обеспечивает асинхронное подключение и управление сервисами API.
"""

from t_tech.invest import AsyncClient
from t_tech.invest.constants import INVEST_GRPC_API
from .endpoints.instruments import InstrumentsEndpoint
from .endpoints.market_data import MarketDataEndpoint
from .endpoints.orders import OrdersEndpoint


class TinkoffClient:
    """
    Основной клиент для взаимодействия с Tinkoff Invest API.
    Предоставляет доступ к различным эндпоинтам через единый интерфейс.
    """
    
    def __init__(self, token: str, target: str = INVEST_GRPC_API):
        """
        Инициализирует клиент с токеном доступа.
        
        Args:
            token: Токен для доступа к API Тинькофф Инвестиций
            target: URL сервера API (по умолчанию production)
        """
        self.token = token
        self.target = target
        self._client: AsyncClient = None
        self._services = None
        
        self.instruments: InstrumentsEndpoint = None
        self.market_data: MarketDataEndpoint = None
        self.orders: OrdersEndpoint = None
    
    async def __aenter__(self):
        """
        Асинхронный вход в контекст - устанавливает соединение с API.
        Инициализирует все эндпоинты для работы.
        """
        self._client = AsyncClient(self.token, target=self.target)
        self._services = await self._client.__aenter__()
        
        self.instruments = InstrumentsEndpoint(self._services)
        self.market_data = MarketDataEndpoint(self._services)
        self.orders = OrdersEndpoint(self._services)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Асинхронный выход из контекста - закрывает соединение с API.
        """
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    @property
    def is_connected(self) -> bool:
        """Проверяет, установлено ли соединение с API"""
        return self._client is not None and self._services is not None
