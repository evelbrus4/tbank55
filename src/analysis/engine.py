import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any

class AnalysisEngine:
    """
    Класс для анализа рыночных данных и генерации торговых сигналов.
    Реализует взвешенную систему индикаторов на основе EMA, RSI, MACD и объема.
    """
    def __init__(self):
        # Веса для различных индикаторов (на основе test2.txt)
        self.weights = {
            'ema_trend': 5,      # Тренд по EMA 20/200
            'ema_history': 3,    # История пересечений EMA
            'rsi': 3,           # Индекс относительной силы
            'macd_hist': 4,     # Гистограмма MACD
            'macd_signal': 2,   # Пересечение MACD Line/Signal
            'volume': 3         # Анализ объема
        }

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает технические индикаторы для DataFrame.
        """
        # EMA
        df['ema_20'] = ta.ema(df['close'], length=20)
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # MACD
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df['macd_line'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            df['macd_hist'] = macd['MACDh_12_26_9']
        
        # ATR для расчета стоп-лосса и тейк-профита
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
        return df

    def get_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Анализирует последний ряд данных и возвращает сигнал и его силу.
        """
        if len(df) < 200:
            return {'signal': 'neutral', 'strength': 0, 'info': 'insufficient_data'}

        last_row = df.iloc[-1]
        prev_rows = df.tail(14)
        
        score = 0
        details = {}

        # 1. EMA Trend (Текущий)
        ema_trend = 0
        if last_row['ema_20'] > last_row['ema_200']:
            ema_trend = 1
            score += self.weights['ema_trend']
        elif last_row['ema_20'] < last_row['ema_200']:
            ema_trend = -1
            score -= self.weights['ema_trend']
        details['ema_trend'] = ema_trend

        # 2. EMA History (За последние 14 свечей)
        ema_history = 0
        ema_20_wins = (prev_rows['ema_20'] > prev_rows['ema_200']).sum()
        ema_200_wins = (prev_rows['ema_20'] < prev_rows['ema_200']).sum()
        
        if ema_20_wins > ema_200_wins:
            ema_history = 1
            score += self.weights['ema_history']
        elif ema_200_wins > ema_20_wins:
            ema_history = -1
            score -= self.weights['ema_history']
        details['ema_history'] = ema_history

        # 3. RSI
        rsi_signal = 0
        rsi = last_row['rsi']
        if 50 < rsi < 70:
            rsi_signal = 1
            score += self.weights['rsi']
        elif 30 < rsi < 50:
            rsi_signal = -1
            score -= self.weights['rsi']
        details['rsi'] = rsi_signal
        details['rsi_value'] = rsi

        # 4. MACD Histogram
        macd_hist_signal = 0
        if last_row['macd_hist'] > 0:
            macd_hist_signal = 1
            score += self.weights['macd_hist']
        elif last_row['macd_hist'] < 0:
            macd_hist_signal = -1
            score -= self.weights['macd_hist']
        details['macd_hist'] = macd_hist_signal

        # 5. MACD Line/Signal
        macd_signal = 0
        if last_row['macd_line'] > last_row['macd_signal']:
            macd_signal = 1
            score += self.weights['macd_signal']
        elif last_row['macd_line'] < last_row['macd_signal']:
            macd_signal = -1
            score -= self.weights['macd_signal']
        details['macd_signal'] = macd_signal

        # 6. Volume
        volume_signal = 0
        avg_vol = prev_rows['volume'].mean()
        vol_count = 0
        for vol in prev_rows['volume']:
            if vol > avg_vol: vol_count += 1
            elif vol < avg_vol: vol_count -= 1
            
        if vol_count > 0:
            volume_signal = 1
            score += self.weights['volume']
        elif vol_count < 0:
            volume_signal = -1
            score -= self.weights['volume']
        details['volume_signal'] = volume_signal

        # Итоговый сигнал
        # Пороги из test2.txt: 10 / -10
        signal = 'neutral'
        if score >= 10:
            signal = 'long'
        elif score <= -10:
            signal = 'short'
            
        # Расчет уровней стоп-лосса и тейк-профита на основе ATR
        atr = last_row['atr']
        current_price = last_row['close']
        
        # Стоп-лосс: 2 ATR от текущей цены
        # Тейк-профит: 3 ATR от текущей цены
        stop_loss_distance = atr * 2
        take_profit_distance = atr * 3
        
        if signal == 'long':
            stop_loss = current_price - stop_loss_distance
            take_profit = current_price + take_profit_distance
        elif signal == 'short':
            stop_loss = current_price + stop_loss_distance
            take_profit = current_price - take_profit_distance
        else:
            stop_loss = None
            take_profit = None
        
        return {
            'signal': signal,
            'strength': score,
            'details': details,
            'max_score': sum(self.weights.values()),
            'atr': float(atr),
            'stop_loss': float(stop_loss) if stop_loss else None,
            'take_profit': float(take_profit) if take_profit else None
        }
