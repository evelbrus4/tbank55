import asyncio
import os
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from dotenv import load_dotenv

from src.core.bot import TInvestBot
from src.analysis.engine import AnalysisEngine
from src.storage.virtual_portfolio import VirtualPortfolio
from src.storage.market_data_storage import MarketDataStorage
from src.utils.converters import quotation_to_decimal

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("INVEST_TOKEN")

async def run_monitoring():
    """
    Основной цикл мониторинга рынка для выбранных фьючерсов.
    """
    if not TOKEN:
        print("Ошибка: INVEST_TOKEN не найден в .env")
        return

    engine = AnalysisEngine()
    portfolio = VirtualPortfolio()
    market_data = MarketDataStorage()
    
    # FIGI выбранных инструментов
    TARGET_INSTRUMENTS = {
        "SVH6": "FUTSILV03260",
        "GDH6": "FUTGOLD03260"
    }
    
    # Словарь для хранения коэффициентов плеч
    leverage_info = {}
    
    async with TInvestBot(TOKEN) as bot:
        print(f"Бот запущен. Загрузка информации о фьючерсах...")
        
        # Загружаем коэффициенты плеч для каждого инструмента
        for ticker, figi in TARGET_INSTRUMENTS.items():
            try:
                future_data = await bot.get_future_info(figi)
                klong = quotation_to_decimal(future_data.instrument.klong)
                kshort = quotation_to_decimal(future_data.instrument.kshort)
                leverage_info[ticker] = {
                    'klong': float(klong),
                    'kshort': float(kshort)
                }
                print(f"  {ticker}: KLong={klong:.2f}, KShort={kshort:.2f}")
            except Exception as e:
                print(f"  Ошибка загрузки данных для {ticker}: {e}")
                leverage_info[ticker] = {'klong': 1.0, 'kshort': 1.0}
        
        print(f"\nМониторинг инструментов: {', '.join(TARGET_INSTRUMENTS.keys())}")
        
        while True:
            print(f"\n--- Цикл обновления: {datetime.now().strftime('%H:%M:%S')} ---")
            
            # Показываем статус торговли
            from src.utils.trading_restrictions import TradingRestrictions
            trading_status = TradingRestrictions.get_trading_status_info()
            
            status_icon = "🟢" if trading_status['can_trade'] else "🔴"
            status_text = "Торговля разрешена" if trading_status['can_trade'] else f"Торговля запрещена: {trading_status['reason']}"
            
            print(f"\n{status_icon} {status_text}")
            print(f"⏰ Время работы: {trading_status['trading_hours']}")
            print(f"🕐 Ваше время: {trading_status['current_time']} ({trading_status['timezone']})")
            
            if trading_status['status'] == 'trading':
                print(f"⏳ До закрытия: {trading_status['time_until_event']}")
            elif trading_status['status'] == 'clearing':
                print(f"🔄 Клиринг - возобновление через: {trading_status['time_until_event']}")
            elif trading_status['status'] == 'before_open':
                print(f"⏳ До открытия: {trading_status['time_until_event']}")
            elif trading_status['status'] == 'after_close':
                print(f"💤 Биржа закрыта - открытие через: {trading_status['time_until_event']}")
            
            if trading_status['is_weekend']:
                print(f"📅 Выходной день")
            if trading_status['is_holiday']:
                print(f"🎉 Праздничный день")
            
            print()  # Пустая строка для разделения
            
            # Закрываем позиции, не входящие в TARGET_INSTRUMENTS
            for ticker in list(portfolio.data["positions"].keys()):
                if ticker not in TARGET_INSTRUMENTS:
                    print(f"⚠️  Закрытие старой позиции: {ticker}")
                    portfolio.update_position(ticker, 0, Decimal("0"))
            
            for ticker, figi in TARGET_INSTRUMENTS.items():
                try:
                    # Загружаем данные (для фьючерсов используем минутные свечи)
                    to_date = datetime.now()
                    from_date = to_date - timedelta(days=2)
                    
                    candles_data = []
                    async for candle in bot.get_candles(figi, from_date, to_date, 1):
                        candles_data.append({
                            'time': candle.time,
                            'open': float(quotation_to_decimal(candle.open)),
                            'high': float(quotation_to_decimal(candle.high)),
                            'low': float(quotation_to_decimal(candle.low)),
                            'close': float(quotation_to_decimal(candle.close)),
                            'volume': candle.volume
                        })
                    
                    if len(candles_data) < 200:
                        print(f"Skipping {ticker}: недостаточно данных ({len(candles_data)} свечей)")
                        continue
                        
                    df = pd.DataFrame(candles_data)
                    df = engine.calculate_indicators(df)
                    signal_data = engine.get_signal(df)
                    
                    current_price = quotation_to_decimal(candle.close)
                    
                    # Сохраняем рыночные данные для дашборда
                    market_data.update_instrument_data(
                        ticker=ticker,
                        df=df,
                        current_price=float(current_price),
                        atr=signal_data['atr'],
                        signal=signal_data['signal'],
                        strength=signal_data['strength']
                    )
                    
                    # Проверка стоп-лосса и тейк-профита для открытых позиций
                    exit_reason = portfolio.check_stop_loss_take_profit(ticker, current_price)
                    if exit_reason:
                        print(f"⚠️  {ticker}: Закрытие по {exit_reason.upper()} | Цена: {current_price:.2f}")
                        portfolio.update_position(ticker, 0, current_price)
                        continue
                    
                    print(f"Актив: {ticker:6} | Сила: {signal_data['strength']:3} | Сигнал: {signal_data['signal']:7} | Цена: {current_price:.2f} | ATR: {signal_data['atr']:.2f}")
                    
                    # Логика принятия решения с учетом асимметрии плеч и реальной стоимости контракта
                    target_lots = 0
                    strength = signal_data['strength']
                    
                    # Получаем коэффициенты плеч для текущего инструмента
                    klong = leverage_info.get(ticker, {}).get('klong', 1.0)
                    kshort = leverage_info.get(ticker, {}).get('kshort', 1.0)
                    
                    # Рассчитываем максимальный размер позиции (не более 20% от баланса)
                    current_balance = float(portfolio.data["balance"])
                    max_position_value = current_balance * 0.20  # 20% от баланса
                    
                    # Стоимость 1 лота = текущая цена
                    lot_cost = float(current_price)
                    max_lots = int(max_position_value / lot_cost)
                    
                    # Ограничиваем минимум 1 лот, максимум по балансу
                    max_lots = max(1, min(max_lots, 10))  # Не более 10 лотов для безопасности
                    
                    # Базовые размеры позиций (теперь в процентах от максимума)
                    if signal_data['signal'] == 'long':
                        base_percent = 0
                        if strength >= 17: base_percent = 1.0  # 100% от максимума
                        elif strength >= 14: base_percent = 0.75  # 75%
                        elif strength >= 11: base_percent = 0.5   # 50%
                        else: base_percent = 0.25  # 25%
                        
                        base_lots = max(1, int(max_lots * base_percent))
                        # Корректируем размер с учетом klong (для long позиций используем отрицательные лоты)
                        target_lots = -int(base_lots * (klong / max(klong, kshort)))
                        
                    elif signal_data['signal'] == 'short':
                        base_percent = 0
                        if strength <= -17: base_percent = 1.0
                        elif strength <= -14: base_percent = 0.75
                        elif strength <= -11: base_percent = 0.5
                        else: base_percent = 0.25
                        
                        base_lots = max(1, int(max_lots * base_percent))
                        # Корректируем размер с учетом kshort (для short позиций используем положительные лоты)
                        target_lots = int(base_lots * (kshort / max(klong, kshort)))
                    
                    # Проверка достаточности средств
                    position_cost = abs(target_lots) * lot_cost
                    if position_cost > current_balance * 0.25:  # Не более 25% от баланса на одну сделку
                        print(f"   ⚠️ Позиция слишком большая ({position_cost:.2f} ₽), уменьшаем...")
                        target_lots = int(target_lots * 0.5)  # Уменьшаем вдвое
                    
                    # Передаем уровни стоп-лосса и тейк-профита
                    stop_loss = Decimal(str(signal_data['stop_loss'])) if signal_data['stop_loss'] else None
                    take_profit = Decimal(str(signal_data['take_profit'])) if signal_data['take_profit'] else None
                    
                    # Передаем ATR для расчета проскальзывания и спреда
                    portfolio.update_position(
                        ticker=ticker, 
                        target_lots=target_lots, 
                        current_price=current_price, 
                        stop_loss=stop_loss, 
                        take_profit=take_profit,
                        atr=signal_data['atr']
                    )
                    
                    if target_lots != 0:
                        sl_str = f"{float(stop_loss):.2f}" if stop_loss else "N/A"
                        tp_str = f"{float(take_profit):.2f}" if take_profit else "N/A"
                        print(f"   → Открыта позиция: {target_lots} лотов | SL: {sl_str} | TP: {tp_str}")
                    
                except Exception as e:
                    print(f"Ошибка при обработке {ticker}: {e}")
                
                await asyncio.sleep(0.5)
            
            # Вывод сводки по портфелю
            summary = portfolio.get_portfolio_summary()
            print(f"\n💰 Баланс: {float(summary['balance']):,.2f} ₽ | Открытых позиций: {len(summary['positions'])}")
            
            # Вывод затрат
            total_commission = float(summary.get('total_commission', 0))
            total_slippage = float(summary.get('total_slippage_cost', 0))
            total_spread = float(summary.get('total_spread_cost', 0))
            if total_commission > 0 or total_slippage > 0 or total_spread > 0:
                print(f"📊 Затраты: Комиссии {total_commission:.2f} ₽ | Проскальзывание {total_slippage:.2f} ₽ | Спред {total_spread:.2f} ₽")
            
            if summary['positions']:
                for pos in summary['positions']:
                    pnl = float(pos.get('unrealized_pnl', 0))
                    pnl_sign = "+" if pnl >= 0 else ""
                    print(f"   {pos['ticker']}: {pos['lots']} лотов | P&L: {pnl_sign}{pnl:.2f} ₽")
            
            # Вывод метрик производительности каждые 10 циклов
            if hasattr(portfolio, '_cycle_counter'):
                portfolio._cycle_counter += 1
            else:
                portfolio._cycle_counter = 1
            
            if portfolio._cycle_counter % 10 == 0:
                try:
                    metrics = portfolio.get_performance_metrics()
                    if 'error' not in metrics:
                        print(f"\n📈 Метрики производительности:")
                        print(f"   Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
                        print(f"   Profit Factor: {metrics.get('profit_factor', 0):.2f}")
                        print(f"   Win Rate: {metrics['win_rate']['win_rate_percent']:.1f}%")
                        print(f"   Max Drawdown: {metrics['max_drawdown']['max_drawdown_percent']:.2f}%")
                        print(f"   Total Return: {metrics.get('total_return_percent', 0):.2f}%")
                except Exception as e:
                    print(f"   Ошибка расчета метрик: {e}")
            
            # Для фьючерсов можно уменьшить ожидание до 30 секунд
            await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(run_monitoring())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем.")
