# Работа с маржой для фьючерсов

## Обзор

Система поддерживает маржинальную торговлю фьючерсами через T-Invest API. При работе с фьючерсами используется маржинальное обеспечение вместо полной стоимости контракта.

## Основные концепции

### Маржа (Margin)
Залоговое обеспечение, которое резервируется при открытии позиции по фьючерсу. Обычно составляет 10-20% от стоимости контракта.

### Типы баланса

1. **Total Balance** - Общий баланс счета
   - Начальный баланс + реализованный профит от закрытых сделок
   - Включает зарезервированную маржу

2. **Used Margin** - Используемая маржа
   - Сумма, зарезервированная под открытые позиции
   - Не может быть использована для открытия новых позиций

3. **Free Balance** - Свободные средства
   - `Total Balance - Used Margin`
   - Доступны для открытия новых позиций

4. **Unrealized P&L** - Нереализованная прибыль/убыток
   - Текущий профит по открытым позициям
   - Не влияет на баланс до закрытия позиции

## Получение маржинальных требований из T-Invest API

### 1. Маржа для конкретного фьючерса

```python
from t_tech.invest import Client
from src.storage.margin_calculator import MarginCalculator

# Инициализация
client = Client(token="YOUR_TOKEN")
margin_calc = MarginCalculator(client)

# Получение маржи для фьючерса
figi = "FUTSI0326000"  # FIGI фьючерса
margin_long = margin_calc.get_futures_margin(figi, is_long=True)
margin_short = margin_calc.get_futures_margin(figi, is_long=False)

print(f"Маржа для long: {margin_long} ₽")
print(f"Маржа для short: {margin_short} ₽")
```

### 2. Расчет требуемой маржи для позиции

```python
# Расчет маржи для 10 лотов
required_margin = margin_calc.calculate_required_margin(
    figi="FUTSI0326000",
    lots=10,
    is_long=True
)
print(f"Требуется маржи: {required_margin} ₽")
```

### 3. Проверка маржинальных показателей счета

```python
# Получение маржинальных атрибутов
margin_attrs = margin_calc.check_margin_sufficiency(account_id="YOUR_ACCOUNT_ID")

print(f"Ликвидный портфель: {margin_attrs['liquid_portfolio']}")
print(f"Начальная маржа: {margin_attrs['starting_margin']}")
print(f"Минимальная маржа: {margin_attrs['minimal_margin']}")
print(f"Уровень достаточности: {margin_attrs['funds_sufficiency_level']}")
```

## Работа с VirtualPortfolio

### Открытие позиции с маржой

```python
from decimal import Decimal
from src.storage.virtual_portfolio import VirtualPortfolio
from src.storage.margin_calculator import MarginCalculator

# Инициализация
portfolio = VirtualPortfolio(client=client)
margin_calc = MarginCalculator(client)

# Получаем маржу для инструмента
figi = "FUTSI0326000"
margin_per_lot = margin_calc.get_futures_margin(figi, is_long=True)

# Открываем позицию
portfolio.update_position(
    ticker="SiH6",
    target_lots=-10,  # -10 для long, +10 для short
    current_price=Decimal("90000.0"),
    stop_loss=Decimal("89000.0"),
    take_profit=Decimal("91000.0"),
    figi=figi,
    margin_per_lot=margin_per_lot
)
```

### Проверка достаточности средств

```python
# Проверяем, можем ли открыть позицию
available = portfolio.data["balance"] - portfolio.data["used_margin"]
required = margin_per_lot * 10

if margin_calc.can_open_position(available, required):
    print("Достаточно средств для открытия позиции")
else:
    print("Недостаточно средств")
```

### Закрытие позиции

```python
# При закрытии позиции:
# 1. Освобождается зарезервированная маржа
# 2. К балансу добавляется профит/убыток
portfolio.update_position(
    ticker="SiH6",
    target_lots=0,  # 0 = закрыть позицию
    current_price=Decimal("91000.0")
)
```

## Логика работы с балансом

### При открытии позиции:
1. Рассчитывается требуемая маржа: `margin_per_lot * abs(lots)`
2. Проверяется достаточность средств: `free_balance >= required_margin`
3. Маржа резервируется:
   - `balance -= required_margin`
   - `used_margin += required_margin`
4. Баланс НЕ изменяется на стоимость контракта

### При закрытии позиции:
1. Рассчитывается профит: `(close_price - entry_price) * lots`
2. Освобождается маржа:
   - `balance += margin + profit`
   - `used_margin -= margin`
3. Реализованный профит добавляется к балансу

## Пример расчета

### Начальное состояние:
- Total Balance: 1,000,000 ₽
- Used Margin: 0 ₽
- Free Balance: 1,000,000 ₽

### Открываем long позицию:
- Инструмент: SiH6 (фьючерс на доллар)
- Лоты: 10
- Цена входа: 90,000 ₽
- Маржа на лот: 9,000 ₽ (10% от стоимости)
- Требуемая маржа: 90,000 ₽

**После открытия:**
- Total Balance: 910,000 ₽ (1,000,000 - 90,000)
- Used Margin: 90,000 ₽
- Free Balance: 820,000 ₽ (910,000 - 90,000)

### Закрываем позицию с профитом:
- Цена закрытия: 91,000 ₽
- Профит: (91,000 - 90,000) × 10 = 10,000 ₽

**После закрытия:**
- Total Balance: 1,010,000 ₽ (910,000 + 90,000 + 10,000)
- Used Margin: 0 ₽
- Free Balance: 1,010,000 ₽
- Realized P&L: +10,000 ₽

## API методы T-Invest

### InstrumentsService.get_futures_margin()
Возвращает маржинальные требования для фьючерса:
- `initial_margin_on_buy` - маржа для long позиции
- `initial_margin_on_sell` - маржа для short позиции
- `min_price_increment` - минимальный шаг цены
- `min_price_increment_amount` - стоимость шага

### UsersService.get_margin_attributes()
Возвращает маржинальные показатели счета:
- `liquid_portfolio` - ликвидная стоимость портфеля
- `starting_margin` - начальная маржа
- `minimal_margin` - минимальная маржа
- `funds_sufficiency_level` - уровень достаточности средств (должен быть > 1)
- `amount_of_missing_funds` - недостающая сумма

## Риски и ограничения

### Ликвидация позиции
Если убыток по позиции превышает зарезервированную маржу, позиция может быть ликвидирована брокером.

### Уровень достаточности средств
- Если `funds_sufficiency_level <= 1.0` - критический уровень
- Рекомендуется поддерживать уровень > 1.5

### Запас средств
При открытии позиции рекомендуется оставлять запас свободных средств (20-30% от требуемой маржи).

## Интеграция с ботом

```python
from t_tech.invest import Client
from src.storage.virtual_portfolio import VirtualPortfolio
from src.storage.margin_calculator import MarginCalculator

# Инициализация
client = Client(token="YOUR_TOKEN")
portfolio = VirtualPortfolio(client=client)
margin_calc = MarginCalculator(client)

# В стратегии торговли
def open_position(ticker, figi, lots, price, stop_loss, take_profit):
    # Получаем маржу
    is_long = lots < 0
    margin_per_lot = margin_calc.get_futures_margin(figi, is_long)
    
    # Проверяем достаточность средств
    required_margin = margin_per_lot * abs(lots)
    free_balance = portfolio.data["balance"] - portfolio.data["used_margin"]
    
    if not margin_calc.can_open_position(free_balance, required_margin):
        print("Недостаточно средств для открытия позиции")
        return False
    
    # Открываем позицию
    portfolio.update_position(
        ticker=ticker,
        target_lots=lots,
        current_price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        figi=figi,
        margin_per_lot=margin_per_lot
    )
    return True
```

## Мониторинг в Dashboard

Dashboard отображает:
- **Total Balance** - общий баланс
- **Used Margin** - используемая маржа
- **Free Balance** - свободные средства
- **Realized P&L** - реализованный профит
- **Active Positions** - количество открытых позиций

Для каждой позиции показывается:
- Направление (LONG/SHORT)
- Количество лотов
- Цена входа
- Стоимость позиции
- **Зарезервированная маржа**
- Stop Loss / Take Profit
