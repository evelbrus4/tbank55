import streamlit as st
import json
import os
import sys
from datetime import datetime
import pandas as pd
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.trading_restrictions import TradingRestrictions
import importlib
import copy

# Настройка страницы
st.set_page_config(page_title="Дашборд T-Invest Бота", layout="wide")

def load_portfolio_data(file_path="data/portfolio.json"):
    """Загружает данные портфеля для отображения."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_market_data(file_path="data/market_data.json"):
    """Загружает рыночные данные для отображения."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_config():
    """Загружает текущую конфигурацию бота."""
    try:
        # Импортируем модуль конфигурации
        import src.config.trading_config as config_module
        importlib.reload(config_module)
        
        active_config = config_module.ACTIVE_CONFIG
        
        return {
            'slippage': active_config.SLIPPAGE_CONFIG,
            'spread': active_config.SPREAD_CONFIG,
            'order_execution': active_config.ORDER_EXECUTION_CONFIG,
            'risk': active_config.RISK_CONFIG,
            'metrics': active_config.METRICS_CONFIG,
            'general': active_config.GENERAL_CONFIG,
            'strategy': active_config.STRATEGY_CONFIG,
            'active_preset': active_config.__name__
        }
    except Exception as e:
        st.error(f"Ошибка загрузки конфигурации: {e}")
        return None

def reset_config_to_default():
    """Сбрасывает конфигурацию на значения по умолчанию (TradingConfig)."""
    try:
        config_path = "config/trading_config.py"
        
        # Читаем файл
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Меняем ACTIVE_CONFIG на TradingConfig
        import re
        content = re.sub(
            r'ACTIVE_CONFIG = \w+',
            'ACTIVE_CONFIG = TradingConfig',
            content
        )
        
        # Сохраняем
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        st.error(f"Ошибка сброса конфигурации: {e}")
        return False

def reset_portfolio():
    """Полный сброс портфеля: удаляет историю и возвращает начальный баланс."""
    try:
        portfolio_path = "data/portfolio.json"
        
        # Создаем новый портфель с начальными значениями
        fresh_portfolio = {
            "balance": "200000.0",
            "initial_balance": "200000.0",
            "positions": {},
            "history": [],
            "used_margin": "0",
            "total_commission": "0",
            "total_slippage_cost": "0",
            "total_spread_cost": "0",
            "next_trade_id": 1,
            "balance_history": [],
            "atr_history": {}
        }
        
        # Сохраняем
        with open(portfolio_path, 'w', encoding='utf-8') as f:
            json.dump(fresh_portfolio, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        st.error(f"Ошибка сброса портфеля: {e}")
        return False

def save_custom_config(config_data):
    """Сохраняет пользовательскую конфигурацию в файл."""
    try:
        config_path = "config/trading_config.py"
        
        # Читаем текущий файл
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        
        # Обновляем каждую секцию
        section_map = {
            'slippage': 'SLIPPAGE_CONFIG',
            'spread': 'SPREAD_CONFIG',
            'risk': 'RISK_CONFIG',
            'metrics': 'METRICS_CONFIG',
            'general': 'GENERAL_CONFIG',
            'strategy': 'STRATEGY_CONFIG'
        }
        
        for section_key, section_name in section_map.items():
            if section_key not in config_data:
                continue
            
            section_data = config_data[section_key]
            
            # Находим секцию в файле
            pattern = f"{section_name}.*?=.*?{{(.*?)}}"
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                old_section = match.group(0)
                
                # Обновляем каждый параметр в секции
                new_section = old_section
                for key, value in section_data.items():
                    # Форматируем значение
                    if isinstance(value, bool):
                        value_str = str(value)
                    elif isinstance(value, str):
                        value_str = f"'{value}'"
                    elif isinstance(value, float):
                        # Форматируем float без лишних нулей
                        value_str = f"{value:.10g}"
                    else:
                        value_str = str(value)
                    
                    # Заменяем значение, сохраняя комментарий
                    key_pattern = f"('{key}'\\s*:\\s*)([^,#]+)(.*)"
                    new_section = re.sub(key_pattern, f"\\g<1>{value_str}\\g<3>", new_section)
                
                content = content.replace(old_section, new_section)
        
        # Сохраняем обратно
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения конфигурации: {e}")
        import traceback
        st.error(traceback.format_exc())
        return False

def create_ohlc_chart(candles_data, ticker, portfolio_history=None):
    """
    Создает интерактивный график свечей с индикаторами.
    
    Args:
        candles_data: Список словарей со свечами
        ticker: Тикер инструмента
        portfolio_history: История сделок для отметок
    """
    df = pd.DataFrame(candles_data)
    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except (ValueError, pd.errors.OutOfBoundsDatetime) as e:
        print(f"Ошибка парсинга timestamp: {e}")
        # Создаем искусственные timestamp на основе индекса
        df['timestamp'] = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq='1min')
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, 
                        subplot_titles=(f'{ticker} - Цена', 'RSI'), 
                        row_heights=[0.7, 0.3])

    # Свечи
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='OHLC'
    ), row=1, col=1)

    # EMA индикаторы
    if 'ema_20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'], 
            y=df['ema_20'], 
            name='EMA 20', 
            line=dict(color='blue', width=1)
        ), row=1, col=1)
    try:
        if 'ema_200' in df.columns:
            df['ema_200'] = pd.to_numeric(df['ema_200'], errors='coerce')
    except Exception as e:
        print(f"Ошибка обработки ema_200: {e}")
    if 'ema_200' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'], 
            y=df['ema_200'], 
            name='EMA 200', 
            line=dict(color='red', width=1)
        ), row=1, col=1)

    # Отметки входа/выхода из позиций
    if portfolio_history:
        for trade in portfolio_history:
            if trade.get('ticker') == ticker:
                trade_time = pd.to_datetime(trade['timestamp'])
                trade_price = float(trade['price'])
                
                if trade['action'] == 'update':
                    # Зеленый маркер для открытия
                    direction = 'LONG' if trade['lots'] < 0 else 'SHORT'
                    fig.add_trace(go.Scatter(
                        x=[trade_time],
                        y=[trade_price],
                        mode='markers',
                        marker=dict(size=12, color='green', symbol='triangle-up'),
                        name=f'Открытие {direction}',
                        showlegend=False
                    ), row=1, col=1)
                elif trade['action'] == 'close':
                    # Красный маркер для закрытия
                    fig.add_trace(go.Scatter(
                        x=[trade_time],
                        y=[trade_price],
                        mode='markers',
                        marker=dict(size=12, color='red', symbol='triangle-down'),
                        name='Закрытие',
                        showlegend=False
                    ), row=1, col=1)

    # RSI
    if 'rsi' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'], 
            y=df['rsi'], 
            name='RSI', 
            line=dict(color='purple', width=1)
        ), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(
        height=600, 
        showlegend=True, 
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    fig.update_xaxes(title_text="Время", row=2, col=1)
    fig.update_yaxes(title_text="Цена", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    
    return fig

def main():
    st.title("Дашборд торгового бота T-Invest")
    
    # Боковая панель
    st.sidebar.header("⚙️ Панель управления")
    
    # Вкладки в сайдбаре
    sidebar_tab = st.sidebar.radio(
        "Выберите раздел:",
        ["📊 Обзор", "⚙️ Конфигурация"],
        label_visibility="collapsed"
    )
    
    if sidebar_tab == "📊 Обзор":
        st.sidebar.markdown("### 📊 Обзор")
        update_interval = st.sidebar.slider("Интервал обновления (сек)", 5, 60, 5)
        auto_refresh = st.sidebar.checkbox("Автообновление", value=True)
        
        # Время последнего обновления
        st.sidebar.info(f"Последнее обновление: {datetime.now().strftime('%H:%M:%S')}")
        
        # Статус торговли
        st.sidebar.markdown("---")
        st.sidebar.subheader("Статус торговли")
        
        try:
            trading_status = TradingRestrictions.get_trading_status_info()
            
            if trading_status['can_trade']:
                st.sidebar.success("🟢 Торговля разрешена")
            else:
                st.sidebar.warning(f"🔴 {trading_status['reason']}")
            
            st.sidebar.markdown(f"**⏰ Время работы:** {trading_status['trading_hours']}")
            st.sidebar.markdown(f"**🕐 Ваше время:** {trading_status['current_time']} ({trading_status['timezone']})")
            
            if trading_status['status'] == 'trading':
                st.sidebar.markdown(f"**⏳ До закрытия:** {trading_status['time_until_event']}")
            elif trading_status['status'] == 'clearing':
                st.sidebar.markdown(f"**🔄 Клиринг:** {trading_status['time_until_event']}")
            elif trading_status['status'] == 'before_open':
                st.sidebar.markdown(f"**⏳ До открытия:** {trading_status['time_until_event']}")
            elif trading_status['status'] == 'after_close':
                st.sidebar.markdown(f"**💤 До открытия:** {trading_status['time_until_event']}")
        except Exception as e:
            st.sidebar.error(f"Ошибка получения статуса: {e}")
            # Fallback на старый метод
            can_trade, reason = TradingRestrictions.can_trade()
            if can_trade:
                st.sidebar.success("🟢 Торговля разрешена")
            else:
                st.sidebar.warning(f"🔴 Торговля запрещена\n\n{reason}")
    
    else:  # Конфигурация
        st.sidebar.markdown("### ⚙️ Настройки бота")
        
        # Загружаем текущую конфигурацию
        current_config = load_config()
        
        if current_config:
            # Инициализируем session_state для хранения изменений
            if 'config_changes' not in st.session_state:
                st.session_state.config_changes = {}
            
            # Редактируемые секции
            with st.sidebar.expander("🎯 Проскальзывание (Slippage)", expanded=False):
                slippage = current_config['slippage'].copy()
                slippage['enabled'] = st.checkbox("Включено", value=slippage['enabled'], key="slippage_enabled")
                slippage['base_slippage_percent'] = st.slider("Базовое (%)", 0.0, 1.0, slippage['base_slippage_percent'], 0.01, key="slippage_base", disabled=not slippage['enabled'])
                slippage['volume_factor_per_10_lots'] = st.slider("Фактор объема", 0.0, 0.1, slippage['volume_factor_per_10_lots'], 0.001, key="slippage_volume", disabled=not slippage['enabled'])
                slippage['volatility_multiplier'] = st.slider("Множитель волатильности", 0.0, 5.0, slippage['volatility_multiplier'], 0.1, key="slippage_vol", disabled=not slippage['enabled'])
                slippage['max_slippage_percent'] = st.slider("Максимум (%)", 0.0, 2.0, slippage['max_slippage_percent'], 0.1, key="slippage_max", disabled=not slippage['enabled'])
                st.session_state.config_changes['slippage'] = slippage
            
            with st.sidebar.expander("📊 Спред Bid/Ask", expanded=False):
                spread = current_config['spread'].copy()
                spread['enabled'] = st.checkbox("Включено", value=spread['enabled'], key="spread_enabled")
                spread['base_spread_percent'] = st.slider("Базовый спред (%)", 0.0, 0.5, spread['base_spread_percent'], 0.01, key="spread_base", disabled=not spread['enabled'])
                spread['volatility_multiplier'] = st.slider("Множитель волатильности", 0.0, 5.0, spread['volatility_multiplier'], 0.1, key="spread_vol", disabled=not spread['enabled'])
                spread['min_spread_percent'] = st.slider("Минимум (%)", 0.0, 0.1, spread['min_spread_percent'], 0.001, key="spread_min", disabled=not spread['enabled'])
                spread['max_spread_percent'] = st.slider("Максимум (%)", 0.0, 1.0, spread['max_spread_percent'], 0.01, key="spread_max", disabled=not spread['enabled'])
                st.session_state.config_changes['spread'] = spread
            
            with st.sidebar.expander("🛡️ Риск-менеджмент", expanded=False):
                risk = current_config['risk'].copy()
                risk['enabled'] = st.checkbox("Включено", value=risk['enabled'], key="risk_enabled")
                risk['max_drawdown_percent'] = st.slider("Макс. просадка (%)", 0.0, 50.0, risk['max_drawdown_percent'], 1.0, key="risk_drawdown", disabled=not risk['enabled'])
                risk['risk_per_trade_percent'] = st.slider("Риск на сделку (%)", 0.0, 10.0, risk['risk_per_trade_percent'], 0.5, key="risk_per_trade", disabled=not risk['enabled'])
                risk['max_open_positions'] = st.slider("Макс. открытых позиций", 1, 20, risk['max_open_positions'], 1, key="risk_max_pos", disabled=not risk['enabled'])
                risk['daily_loss_limit_percent'] = st.slider("Дневной лимит убытков (%)", 0.0, 20.0, risk['daily_loss_limit_percent'], 1.0, key="risk_daily", disabled=not risk['enabled'])
                risk['max_position_size_percent'] = st.slider("Макс. размер позиции (%)", 0.0, 100.0, risk['max_position_size_percent'], 5.0, key="risk_pos_size", disabled=not risk['enabled'])
                st.session_state.config_changes['risk'] = risk
            
            with st.sidebar.expander("📈 Метрики производительности", expanded=False):
                metrics = current_config['metrics'].copy()
                metrics['enabled'] = st.checkbox("Включено", value=metrics['enabled'], key="metrics_enabled")
                metrics['risk_free_rate'] = st.slider("Безрисковая ставка (%)", 0.0, 10.0, metrics['risk_free_rate'], 0.1, key="metrics_rf", disabled=not metrics['enabled'])
                st.session_state.config_changes['metrics'] = metrics
            
            with st.sidebar.expander("⚙️ Общие настройки", expanded=False):
                general = current_config['general'].copy()
                general['initial_balance'] = st.number_input("Начальный баланс (₽)", value=general['initial_balance'], step=10000.0, key="general_balance")
                general['commission_rate'] = st.slider("Комиссия (%)", 0.0, 1.0, general['commission_rate'] * 100, 0.01, key="general_commission") / 100
                st.session_state.config_changes['general'] = general
            
            with st.sidebar.expander("🎲 Стратегия", expanded=False):
                strategy = current_config['strategy'].copy()
                strategy['max_lots_per_instrument'] = st.slider("Макс. лотов на инструмент", 1, 200, strategy['max_lots_per_instrument'], 10, key="strategy_max_lots")
                strategy['atr_stop_loss_multiplier'] = st.slider("SL множитель ATR", 0.5, 5.0, strategy['atr_stop_loss_multiplier'], 0.1, key="strategy_sl")
                strategy['atr_take_profit_multiplier'] = st.slider("TP множитель ATR", 0.5, 10.0, strategy['atr_take_profit_multiplier'], 0.1, key="strategy_tp")
                st.session_state.config_changes['strategy'] = strategy
            
            st.sidebar.markdown("---")
            
            # Кнопка сохранения
            col1, col2 = st.sidebar.columns(2)
            
            with col1:
                if st.button("💾 Сохранить", use_container_width=True, type="primary"):
                    if save_custom_config(st.session_state.config_changes):
                        st.sidebar.success("✅ Настройки сохранены!")
                        st.sidebar.info("⚠️ Перезапустите бота")
                        st.session_state.config_changes = {}
                    else:
                        st.sidebar.error("❌ Ошибка")
            
            with col2:
                if st.button("🔄 По умолчанию", use_container_width=True):
                    if reset_config_to_default():
                        st.sidebar.success("✅ Сброшено по умолчанию!")
                        st.sidebar.info("⚠️ Обновите страницу (F5)")
                        # Очищаем session_state чтобы при следующей загрузке подтянулись новые значения
                        if 'config_changes' in st.session_state:
                            del st.session_state.config_changes
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Ошибка")
            
            st.sidebar.markdown("---")
            
            # Кнопка полного сброса
            st.sidebar.markdown("### 🗑️ Полный сброс")
            st.sidebar.warning("⚠️ **Внимание!** Это удалит всю историю сделок и вернет баланс к 200,000 ₽")
            
            # Добавляем подтверждение
            confirm_reset = st.sidebar.checkbox("Я понимаю, что это удалит все данные", key="confirm_reset")
            
            if st.sidebar.button("🗑️ Сбросить портфель", use_container_width=True, type="secondary", disabled=not confirm_reset):
                if reset_portfolio():
                    st.sidebar.success("✅ Портфель сброшен!")
                    st.sidebar.info("ℹ️ Обновите страницу")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.sidebar.error("❌ Ошибка")
            
            st.sidebar.markdown("---")
            st.sidebar.info("💡 **Совет:** Измените параметры и нажмите 'Сохранить'.")
            st.sidebar.caption("⚠️ После изменений перезапустите бота.")
        else:
            st.sidebar.error("❌ Не удалось загрузить конфигурацию")
        
        # Устанавливаем значения по умолчанию для переменных, используемых в основном коде
        update_interval = 5
        auto_refresh = False
    
    # Загрузка данных
    portfolio = load_portfolio_data()
    market_data_info = load_market_data()
    
    if portfolio:
        # Расчет метрик
        balance = float(portfolio['balance'])
        used_margin = float(portfolio.get('used_margin', 0))
        free_balance = balance - used_margin
        
        # Расчет нереализованного P&L по открытым позициям
        unrealized_pnl = 0.0
        for ticker, pos in portfolio['positions'].items():
            # Для упрощения используем avg_price как текущую цену
            # В реальности нужно получать текущую рыночную цену
            unrealized_pnl += 0.0  # Пока 0, так как нет текущих цен
        
        # Расчет реализованного профита из истории закрытых сделок
        realized_profit = sum(float(h.get('profit', 0)) for h in portfolio['history'] if h.get('action') == 'close')
        total_commission = float(portfolio.get('total_commission', 0))
        net_profit = realized_profit - total_commission
        
        # Основные метрики
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("Общий баланс", f"{balance:,.2f} ₽", help="Общий баланс (начальный + реализованный профит - комиссии)")
        with col2:
            st.metric("Использ. маржа", f"{used_margin:,.2f} ₽", help="Зарезервированная маржа под открытые позиции")
        with col3:
            st.metric("Свободно", f"{free_balance:,.2f} ₽", help="Свободные средства для открытия новых позиций")
        with col4:
            st.metric("Реализ. прибыль", f"{realized_profit:,.2f} ₽", delta=f"{realized_profit:,.2f}", help="Профит от закрытых сделок (до комиссий)")
        with col5:
            st.metric("Комиссии", f"{total_commission:,.2f} ₽", delta=f"-{total_commission:,.2f}", delta_color="inverse", help="Общая сумма комиссий (0.05% от оборота)")
        with col6:
            st.metric("Открытых позиций", len(portfolio['positions']))

        # Таблица позиций с детальной информацией
        st.subheader("Текущие позиции")
        if portfolio['positions']:
            # Преобразуем данные для красивого отображения
            pos_data = []
            for ticker, pos in portfolio['positions'].items():
                direction = 'LONG' if pos['lots'] < 0 else 'SHORT' if pos['lots'] > 0 else 'NEUTRAL'
                entry_price = float(pos['avg_price'])
                # Для фьючерсов показываем стоимость позиции (цена входа * количество лотов)
                position_value = entry_price * abs(pos['lots'])
                
                margin = float(pos.get('margin', 0))
                
                trade_id = pos.get('trade_id', '-')
                opened_at = pos.get('opened_at', '-')
                accumulated_commission = float(pos.get('accumulated_commission', 0))
                
                # Определяем валюту по тикеру
                # Фьючерсы торгуются в долларах, но цена котируется в рублях
                if 'SV' in ticker:  # Серебро
                    price_currency = "$"
                elif 'GD' in ticker or 'SI' in ticker:  # Золото
                    price_currency = "$"
                else:  # Валюты
                    price_currency = "$"
                
                pos_data.append({
                    '№ сделки': f"#{trade_id}" if trade_id else '-',
                    'Время открытия': opened_at,
                    'Тикер': ticker,
                    'Направление': direction,
                    'Лоты': abs(pos['lots']),
                    'Цена входа': f"{entry_price:.2f} {price_currency}",
                    'Стоимость': f"{position_value:,.2f} {price_currency}",
                    'Маржа': f"{margin:,.2f} ₽",
                    'Накопл. комиссия': f"{accumulated_commission:,.2f} ₽",
                    'Стоп-лосс': f"{float(pos['stop_loss']):.2f} {price_currency}" if pos.get('stop_loss') else 'Нет',
                    'Тейк-профит': f"{float(pos['take_profit']):.2f} {price_currency}" if pos.get('take_profit') else 'Нет'
                })
            
            pos_df = pd.DataFrame(pos_data)
            
            # Применяем цветовую индикацию
            def highlight_direction(row):
                if row['Направление'] == 'LONG':
                    return ['background-color: #90EE90'] * len(row)  # Светло-зеленый
                elif row['Направление'] == 'SHORT':
                    return ['background-color: #FFB6C1'] * len(row)  # Светло-красный
                else:
                    return [''] * len(row)
            
            styled_df = pos_df.style.apply(highlight_direction, axis=1)
            st.dataframe(styled_df, width='stretch', hide_index=True)
        else:
            st.info("Нет открытых позиций")

        # История сделок
        st.subheader("История сделок")
        if portfolio['history']:
            hist_df = pd.DataFrame(portfolio['history'])
            
            # Добавляем вкладки для разделения открытых и закрытых сделок
            tab1, tab2 = st.tabs(["Все сделки", "Закрытые сделки"])
            
            with tab1:
                # Все сделки
                all_trades_display = hist_df.copy()
                
                # Добавляем колонку Direction для понимания LONG/SHORT
                all_trades_display['direction'] = all_trades_display['lots'].apply(
                    lambda x: 'LONG' if x < 0 else 'SHORT' if x > 0 else 'NEUTRAL'
                )
                all_trades_display['lots_abs'] = all_trades_display['lots'].abs()
                
                # Добавляем trade_id и понятное описание действия
                all_trades_display['trade_id_display'] = all_trades_display.apply(
                    lambda x: f"#{x.get('trade_id', '-')}" if x.get('trade_id') else '-', axis=1
                )
                
                def get_action_description(row):
                    if row['action'] == 'close':
                        return 'Закрытие'
                    elif row['action'] == 'update':
                        return f"Изменение ({row['lots_abs']} лотов)"
                    return row['action']
                
                all_trades_display['action_desc'] = all_trades_display.apply(get_action_description, axis=1)
                
                # Добавляем комиссию и цену с валютой для отображения
                all_trades_display['commission_display'] = all_trades_display.apply(
                    lambda x: f"{float(x.get('commission', 0)):,.2f} ₽" if x.get('commission') else '-', axis=1
                )
                
                def format_price_with_currency(row):
                    price = float(row['price'])
                    # Фьючерсы торгуются в долларах
                    return f"{price:.2f} $"
                
                all_trades_display['price_display'] = all_trades_display.apply(format_price_with_currency, axis=1)
                
                display_cols = ['trade_id_display', 'timestamp', 'ticker', 'direction', 'lots_abs', 'action_desc', 'price_display', 'commission_display']
                available_cols = [col for col in display_cols if col in all_trades_display.columns]
                
                # Переименовываем колонки для отображения
                display_df = all_trades_display[available_cols].tail(15).copy()
                display_df.columns = ['№ сделки', 'Время', 'Тикер', 'Направление', 'Лоты', 'Операция', 'Цена', 'Комиссия']
                
                # Цветовая индикация по направлению
                def highlight_direction_all(row):
                    if row['Направление'] == 'LONG':
                        return ['background-color: #E8F5E9'] * len(row)  # Очень светло-зеленый
                    elif row['Направление'] == 'SHORT':
                        return ['background-color: #FFEBEE'] * len(row)  # Очень светло-красный
                    return [''] * len(row)
                
                styled_all = display_df.style.apply(highlight_direction_all, axis=1)
                st.dataframe(styled_all, width='stretch', hide_index=True)
            
            with tab2:
                # Только закрытые сделки
                closed_trades = hist_df[hist_df['action'] == 'close'].copy()
                if not closed_trades.empty:
                    # Для каждой закрытой сделки находим цену открытия
                    enriched_trades = []
                    for idx, close_trade in closed_trades.iterrows():
                        ticker = close_trade['ticker']
                        close_time = close_trade['timestamp']
                        close_price = float(close_trade['price'])
                        lots = close_trade['lots']
                        profit = float(close_trade['profit'])
                        
                        # Ищем последнюю операцию update для этого тикера перед закрытием
                        open_trades = hist_df[
                            (hist_df['ticker'] == ticker) & 
                            (hist_df['action'] == 'update') & 
                            (hist_df['timestamp'] < close_time)
                        ]
                        
                        if not open_trades.empty:
                            # Берем последнюю операцию открытия
                            last_open = open_trades.iloc[-1]
                            open_price = float(last_open['price'])
                            
                            # Рассчитываем процент изменения
                            # Для long позиций (lots < 0): (close - open) / open * 100
                            # Для short позиций (lots > 0): (open - close) / open * 100
                            if lots < 0:  # Long
                                price_change_pct = ((close_price - open_price) / open_price) * 100
                            else:  # Short
                                price_change_pct = ((open_price - close_price) / open_price) * 100
                            
                            profit_pct = (profit / (open_price * abs(lots))) * 100
                        else:
                            open_price = close_price
                            price_change_pct = 0.0
                            profit_pct = 0.0
                        
                        # Получаем комиссию и чистый профит
                        commission = float(close_trade.get('commission', 0))
                        net_profit_trade = float(close_trade.get('net_profit', profit))
                        
                        trade_id = close_trade.get('trade_id', '-')
                        
                        # Фьючерсы торгуются в долларах
                        price_currency = "$"
                        
                        # Определяем результат сделки
                        if net_profit_trade > 0:
                            result = "✅ Успех"
                        elif net_profit_trade < 0:
                            result = "❌ Убыток"
                        else:
                            result = "⚪ В ноль"
                        
                        enriched_trades.append({
                            '№ сделки': f"#{trade_id}" if trade_id else '-',
                            'Время': close_trade['timestamp'],
                            'Тикер': ticker,
                            'Направление': 'LONG' if lots < 0 else 'SHORT',
                            'Лоты': abs(lots),
                            'Цена откр.': f"{open_price:.2f} {price_currency}",
                            'Цена закр.': f"{close_price:.2f} {price_currency}",
                            'Изм. цены %': f"{price_change_pct:+.2f}%",
                            'Профит': f"{profit:,.2f} $",
                            'Комиссия': f"{commission:,.2f} ₽",
                            'Чистый профит': f"{net_profit_trade:,.2f} $",
                            'Результат': result
                        })
                    
                    trades_df = pd.DataFrame(enriched_trades)
                    
                    # Добавляем цветовую индикацию для профита
                    def highlight_profit(row):
                        profit_str = row['Профит'].replace(' ₽', '').replace(',', '')
                        try:
                            profit_val = float(profit_str)
                            if profit_val > 0:
                                return ['background-color: #90EE90'] * len(row)
                            elif profit_val < 0:
                                return ['background-color: #FFB6C1'] * len(row)
                        except:
                            pass
                        return [''] * len(row)
                    
                    styled_closed = trades_df.tail(15).style.apply(highlight_profit, axis=1)
                    st.dataframe(styled_closed, width='stretch', hide_index=True)
                else:
                    st.info("Пока нет закрытых сделок")
    else:
        st.warning("Данные портфеля не найдены. Запустите бота для генерации данных.")

    # Секция анализа рынка и статистики в две колонки
    analysis_col, stats_col = st.columns([2, 1])
    
    with analysis_col:
        st.subheader("Анализ рынка")
    
    with stats_col:
        st.subheader("Статистика сделок")
    
    # Загружаем рыночные данные
    market_data = load_market_data()
    
    # Статистика в правой колонке
    with stats_col:
        if portfolio:
            closed_trades = [h for h in portfolio['history'] if h.get('action') == 'close']
            
            if closed_trades:
                successful_trades = sum(1 for h in closed_trades if float(h.get('net_profit', h.get('profit', 0))) > 0)
                losing_trades = sum(1 for h in closed_trades if float(h.get('net_profit', h.get('profit', 0))) < 0)
                breakeven_trades = sum(1 for h in closed_trades if float(h.get('net_profit', h.get('profit', 0))) == 0)
                total_closed = len(closed_trades)
                
                win_rate = (successful_trades / total_closed * 100) if total_closed > 0 else 0
                
                # Компактное отображение в одну строку
                stat_row1, stat_row2 = st.columns([1, 1])
                
                with stat_row1:
                    st.metric("🎯 Win Rate", f"{win_rate:.0f}%", 
                             delta=f"{successful_trades}/{total_closed}",
                             delta_color="normal")
                
                with stat_row2:
                    # Мини-статистика
                    st.markdown(f"""
                    <div style='font-size: 0.85em; padding: 8px; background-color: #f0f2f6; border-radius: 5px; margin-top: 8px;'>
                        <div style='margin-bottom: 3px;'>✅ <b>{successful_trades}</b> успешных</div>
                        <div style='margin-bottom: 3px;'>❌ <b>{losing_trades}</b> убыточных</div>
                        <div>⚪ <b>{breakeven_trades}</b> в ноль</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Мини-график
                if total_closed > 0:
                    import plotly.graph_objects as go
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=['✅', '❌', '⚪'],
                        values=[successful_trades, losing_trades, breakeven_trades],
                        marker=dict(colors=['#90EE90', '#FFB6C1', '#E0E0E0']),
                        hole=0.4,
                        textinfo='value',
                        textfont=dict(size=14)
                    )])
                    fig_pie.update_layout(
                        height=200,
                        showlegend=False,
                        margin=dict(l=10, r=10, t=10, b=10)
                    )
                    st.plotly_chart(fig_pie, width='stretch')
            else:
                st.info("Пока нет закрытых сделок")
    
    # Анализ рынка в левой колонке
    with analysis_col:
        if market_data and market_data.get('instruments'):
            # Отображаем текущие рыночные метрики
            st.markdown("### Текущие рыночные показатели")
            
            market_cols = st.columns(len(market_data['instruments']))
            for idx, (ticker, data) in enumerate(market_data['instruments'].items()):
                with market_cols[idx]:
                    signal_color = {
                        'long': '�',
                        'short': '🔴',
                        'neutral': '⚪'
                    }.get(data['signal'], '⚪')
                    
                    # Фьючерсы торгуются в долларах
                    currency = "$"
                    
                    st.metric(
                        label=f"{ticker} {signal_color}",
                        value=f"{data['current_price']:.2f} $",
                        delta=f"Сила: {data['strength']}"
                    )
                    st.caption(f"ATR: {data['atr']:.2f} | Сигнал: {data['signal'].upper()}")
                    st.caption(f"Обновлено: {data.get('last_update', 'N/A')}")
        else:
            st.info("Рыночные данные не доступны. Запустите бота для генерации данных.")
    
    # Графики свечей на полную ширину после блока с колонками
    if market_data and market_data.get('instruments'):
        st.subheader("Графики свечей")
        
        # Создаем вкладки для каждого инструмента
        tickers_with_candles = [ticker for ticker, data in market_data['instruments'].items() if data.get('candles')]
        
        if tickers_with_candles:
            tabs = st.tabs(tickers_with_candles)
            
            for idx, ticker in enumerate(tickers_with_candles):
                with tabs[idx]:
                    data = market_data['instruments'][ticker]
                    # Создаем график
                    fig = create_ohlc_chart(
                        data['candles'], 
                        ticker,
                        portfolio.get('history', []) if portfolio else None
                    )
                    st.plotly_chart(fig, width='stretch')
    # Автоматическое обновление
    if auto_refresh:
        time.sleep(update_interval)
        st.rerun()

if __name__ == "__main__":
    main()
