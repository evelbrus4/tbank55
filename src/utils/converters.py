from decimal import Decimal
from t_tech.invest import Quotation

def quotation_to_decimal(quotation: Quotation) -> Decimal:
    """
    Преобразует объект Quotation из API в Decimal для точных расчетов.
    """
    if quotation is None:
        return Decimal('0')
    return Decimal(quotation.units) + Decimal(quotation.nano) / Decimal('1e9')

def decimal_to_quotation(value: Decimal) -> Quotation:
    """
    Преобразует Decimal в объект Quotation для отправки в API.
    """
    units = int(value)
    nano = int((value - units) * Decimal('1e9'))
    return Quotation(units=units, nano=nano)

def money_value_to_decimal(money_value) -> Decimal:
    """
    Преобразует MoneyValue в Decimal.
    """
    if money_value is None:
        return Decimal('0')
    return Decimal(money_value.units) + Decimal(money_value.nano) / Decimal('1e9')
