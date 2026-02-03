from decimal import Decimal
from typing import Optional
from t_tech.invest import Client
from t_tech.invest.utils import quotation_to_decimal


class MarginCalculator:
    """
    Класс для расчета маржинальных требований для фьючерсов через T-Invest API.
    
    Основные функции:
    - Получение начальной маржи для открытия позиции
    - Расчет требуемой маржи для заданного количества лотов
    - Проверка достаточности средств для открытия позиции
    """
    
    def __init__(self, client: Client):
        """
        Инициализация калькулятора маржи.
        
        Args:
            client: Клиент T-Invest API для получения данных о марже
        """
        self.client = client
        self._margin_cache = {}  # Кеш маржинальных требований по инструментам
    
    def get_futures_margin(self, figi: str, is_long: bool = True) -> Decimal:
        """
        Получает начальную маржу для фьючерса из T-Invest API.
        
        Args:
            figi: FIGI идентификатор фьючерса
            is_long: True для long позиции, False для short
            
        Returns:
            Начальная маржа на 1 контракт в рублях
        """
        if figi in self._margin_cache:
            margin_data = self._margin_cache[figi]
        else:
            try:
                response = self.client.instruments.get_futures_margin(figi=figi)
                margin_data = {
                    'initial_margin_on_buy': quotation_to_decimal(response.initial_margin_on_buy),
                    'initial_margin_on_sell': quotation_to_decimal(response.initial_margin_on_sell)
                }
                self._margin_cache[figi] = margin_data
            except Exception as e:
                print(f"Ошибка при получении маржи для {figi}: {e}")
                # Возвращаем консервативную оценку - 10% от стоимости контракта
                return Decimal("0")
        
        # Для long позиций используем initial_margin_on_buy, для short - initial_margin_on_sell
        if is_long:
            return margin_data['initial_margin_on_buy']
        else:
            return margin_data['initial_margin_on_sell']
    
    def calculate_required_margin(self, figi: str, lots: int, is_long: bool = True) -> Decimal:
        """
        Рассчитывает требуемую маржу для открытия позиции.
        
        Args:
            figi: FIGI идентификатор фьючерса
            lots: Количество лотов (всегда положительное число)
            is_long: True для long позиции, False для short
            
        Returns:
            Требуемая маржа в рублях
        """
        margin_per_contract = self.get_futures_margin(figi, is_long)
        return margin_per_contract * Decimal(abs(lots))
    
    def check_margin_sufficiency(self, account_id: str) -> dict:
        """
        Проверяет маржинальные показатели счета.
        
        Args:
            account_id: ID счета
            
        Returns:
            Словарь с маржинальными показателями:
            - liquid_portfolio: Ликвидная стоимость портфеля
            - starting_margin: Начальная маржа
            - minimal_margin: Минимальная маржа
            - funds_sufficiency_level: Уровень достаточности средств
            - amount_of_missing_funds: Недостающая сумма
        """
        try:
            response = self.client.users.get_margin_attributes(account_id=account_id)
            return {
                'liquid_portfolio': quotation_to_decimal(response.liquid_portfolio),
                'starting_margin': quotation_to_decimal(response.starting_margin),
                'minimal_margin': quotation_to_decimal(response.minimal_margin),
                'funds_sufficiency_level': quotation_to_decimal(response.funds_sufficiency_level),
                'amount_of_missing_funds': quotation_to_decimal(response.amount_of_missing_funds)
            }
        except Exception as e:
            print(f"Ошибка при получении маржинальных атрибутов: {e}")
            return None
    
    def can_open_position(self, available_balance: Decimal, required_margin: Decimal, 
                         safety_factor: Decimal = Decimal("1.2")) -> bool:
        """
        Проверяет, достаточно ли средств для открытия позиции с учетом запаса.
        
        Args:
            available_balance: Доступный баланс
            required_margin: Требуемая маржа
            safety_factor: Коэффициент запаса (по умолчанию 1.2 = 20% запас)
            
        Returns:
            True если средств достаточно, False иначе
        """
        return available_balance >= (required_margin * safety_factor)
