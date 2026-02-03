import json
import os
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd


class MarketDataStorage:
    """
    Класс для сохранения и загрузки рыночных данных (свечи, индикаторы, сигналы).
    Данные сохраняются в JSON файл для отображения в дашборде.
    """
    
    def __init__(self, storage_path: str = "data/market_data.json"):
        """
        Инициализация хранилища рыночных данных.
        
        Args:
            storage_path: Путь к файлу для сохранения данных
        """
        self.storage_path = storage_path
        self.data = {
            "last_update": None,
            "instruments": {}  # ticker: {candles, indicators, signals}
        }
        self._load()
    
    def _load(self):
        """Загружает рыночные данные из файла."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Ошибка при загрузке рыночных данных: {e}")
    
    def _save(self):
        """Сохраняет рыночные данные в файл."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка при сохранении рыночных данных: {e}")
    
    def update_instrument_data(self, ticker: str, df: pd.DataFrame, 
                               current_price: float, atr: float, 
                               signal: str, strength: int):
        """
        Обновляет данные по инструменту.
        
        Args:
            ticker: Тикер инструмента
            df: DataFrame со свечами и индикаторами
            current_price: Текущая цена
            atr: Значение ATR
            signal: Торговый сигнал (buy/sell/neutral)
            strength: Сила сигнала
        """
        # Берем последние 100 свечей для графика
        df_last = df.tail(100).copy()
        
        # Конвертируем DataFrame в список словарей для JSON
        candles = []
        now = datetime.now()
        
        for i, (idx, row) in enumerate(df_last.iterrows()):
            # Если индекс - это datetime, используем его
            if hasattr(idx, 'strftime'):
                timestamp_str = idx.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Иначе создаем timestamp на основе текущего времени минус смещение
                # Предполагаем 1-минутные свечи
                candle_time = now - pd.Timedelta(minutes=len(df_last) - i - 1)
                timestamp_str = candle_time.strftime('%Y-%m-%d %H:%M:%S')
            
            candle = {
                "timestamp": timestamp_str,
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row.get('volume', 0))
            }
            
            # Добавляем индикаторы если есть
            if 'ema_20' in row:
                candle['ema_20'] = float(row['ema_20'])
            if 'ema_200' in row:
                candle['ema_200'] = float(row['ema_200'])
            if 'rsi' in row:
                candle['rsi'] = float(row['rsi'])
            
            candles.append(candle)
        
        # Сохраняем данные по инструменту
        self.data["instruments"][ticker] = {
            "candles": candles,
            "current_price": current_price,
            "atr": atr,
            "signal": signal,
            "strength": strength,
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.data["last_update"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._save()
    
    def get_instrument_data(self, ticker: str) -> Dict[str, Any]:
        """
        Получает данные по инструменту.
        
        Args:
            ticker: Тикер инструмента
            
        Returns:
            Словарь с данными инструмента или None
        """
        return self.data["instruments"].get(ticker)
    
    def get_all_instruments(self) -> List[str]:
        """
        Возвращает список всех инструментов с данными.
        
        Returns:
            Список тикеров
        """
        return list(self.data["instruments"].keys())
    
    def clear_old_data(self, max_candles: int = 100):
        """
        Очищает старые данные, оставляя только последние свечи.
        
        Args:
            max_candles: Максимальное количество свечей для хранения
        """
        for ticker in self.data["instruments"]:
            candles = self.data["instruments"][ticker].get("candles", [])
            if len(candles) > max_candles:
                self.data["instruments"][ticker]["candles"] = candles[-max_candles:]
        
        self._save()
