"""
Модуль для проверки торговых ограничений на Московской бирже.
Содержит правила для фьючерсов: торговые часы, выходные, праздники, минимальные размеры позиций.
"""

from datetime import datetime, time
from typing import Tuple


class TradingRestrictions:
    """
    Класс для проверки торговых ограничений на Московской бирже (MOEX).
    
    Правила для фьючерсов:
    - Торговые часы: 10:00 - 23:50 МСК (с клирингом 14:00-14:05 и 18:45-19:00)
    - Выходные: суббота, воскресенье
    - Праздники: официальные праздничные дни РФ
    - Минимальный размер позиции: 1 лот
    """
    
    # Торговые часы для фьючерсов на Московской бирже (МСК)
    TRADING_START = time(10, 0)  # 10:00
    TRADING_END = time(23, 50)   # 23:50
    
    # Клиринговые окна (когда торговля приостановлена)
    CLEARING_WINDOWS = [
        (time(14, 0), time(14, 5)),   # Дневной клиринг
        (time(18, 45), time(19, 0))   # Вечерний клиринг
    ]
    
    # Официальные праздничные дни РФ (нерабочие дни биржи)
    # Формат: (месяц, день)
    HOLIDAYS = [
        (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),  # Новогодние каникулы
        (2, 23),  # День защитника Отечества
        (3, 8),   # Международный женский день
        (5, 1),   # Праздник Весны и Труда
        (5, 9),   # День Победы
        (6, 12),  # День России
        (11, 4),  # День народного единства
    ]
    
    # Минимальный размер позиции
    MIN_POSITION_SIZE = 1  # лот
    
    @staticmethod
    def is_trading_hours(dt: datetime = None) -> Tuple[bool, str]:
        """
        Проверяет, находится ли указанное время в торговых часах.
        
        Args:
            dt: Время для проверки (если None, используется текущее время)
            
        Returns:
            Tuple[bool, str]: (разрешена ли торговля, причина запрета)
        """
        if dt is None:
            dt = datetime.now()
        
        current_time = dt.time()
        
        # Проверка торговых часов
        if current_time < TradingRestrictions.TRADING_START:
            return False, f"Торги еще не начались. Начало в {TradingRestrictions.TRADING_START.strftime('%H:%M')} МСК"
        
        if current_time > TradingRestrictions.TRADING_END:
            return False, f"Торги завершены. Окончание в {TradingRestrictions.TRADING_END.strftime('%H:%M')} МСК"
        
        # Проверка клиринговых окон
        for start, end in TradingRestrictions.CLEARING_WINDOWS:
            if start <= current_time <= end:
                return False, f"Клиринг. Торговля возобновится в {end.strftime('%H:%M')} МСК"
        
        return True, ""
    
    @staticmethod
    def is_trading_day(dt: datetime = None) -> Tuple[bool, str]:
        """
        Проверяет, является ли указанная дата торговым днем.
        
        Args:
            dt: Дата для проверки (если None, используется текущая дата)
            
        Returns:
            Tuple[bool, str]: (торговый ли день, причина запрета)
        """
        if dt is None:
            dt = datetime.now()
        
        # Проверка выходных
        if dt.weekday() >= 5:  # 5 = суббота, 6 = воскресенье
            return False, "Выходной день (суббота/воскресенье)"
        
        # Проверка праздников
        if (dt.month, dt.day) in TradingRestrictions.HOLIDAYS:
            return False, "Праздничный день"
        
        return True, ""
    
    @staticmethod
    def can_trade(dt: datetime = None) -> Tuple[bool, str]:
        """
        Полная проверка возможности торговли (день + время).
        
        Args:
            dt: Дата и время для проверки (если None, используется текущее)
            
        Returns:
            Tuple[bool, str]: (можно ли торговать, причина запрета)
        """
        if dt is None:
            dt = datetime.now()
        
        # Проверка торгового дня
        is_day, day_reason = TradingRestrictions.is_trading_day(dt)
        if not is_day:
            return False, day_reason
        
        # Проверка торговых часов
        is_hours, hours_reason = TradingRestrictions.is_trading_hours(dt)
        if not is_hours:
            return False, hours_reason
        
        return True, ""
    
    @staticmethod
    def validate_position_size(lots: int) -> Tuple[bool, str]:
        """
        Проверяет, соответствует ли размер позиции минимальным требованиям.
        
        Args:
            lots: Количество лотов
            
        Returns:
            Tuple[bool, str]: (валидный ли размер, причина отказа)
        """
        abs_lots = abs(lots)
        
        if abs_lots == 0:
            return True, ""  # Закрытие позиции всегда разрешено
        
        if abs_lots < TradingRestrictions.MIN_POSITION_SIZE:
            return False, f"Минимальный размер позиции: {TradingRestrictions.MIN_POSITION_SIZE} лот"
        
        return True, ""
    
    @staticmethod
    def get_trading_status_info(dt: datetime = None) -> dict:
        """
        Возвращает детальную информацию о статусе торговли.
        
        Args:
            dt: Дата и время для проверки (если None, используется текущее локальное время)
            
        Returns:
            Словарь с информацией о торговле
        """
        from datetime import timedelta
        import time as time_module
        
        if dt is None:
            dt = datetime.now()
        
        # Определяем часовой пояс (локальное время)
        try:
            is_dst = time_module.daylight and time_module.localtime().tm_isdst > 0
            utc_offset = -(time_module.altzone if is_dst else time_module.timezone) / 3600
            timezone_name = f"UTC{'+' if utc_offset >= 0 else ''}{int(utc_offset)}"
        except:
            utc_offset = 0
            timezone_name = "Local"
        
        # Конвертируем локальное время в московское (МСК = UTC+3)
        moscow_offset = 3
        time_diff_hours = moscow_offset - utc_offset
        dt_moscow = dt + timedelta(hours=time_diff_hours)
        current_time_moscow = dt_moscow.time()
        
        # Проверяем возможность торговли (используем московское время)
        can_trade, reason = TradingRestrictions.can_trade(dt_moscow)
        
        # Рассчитываем время до закрытия/открытия (в московском времени)
        time_info = {}
        
        if current_time_moscow < TradingRestrictions.TRADING_START:
            # До открытия
            start_dt = dt_moscow.replace(hour=TradingRestrictions.TRADING_START.hour, 
                                 minute=TradingRestrictions.TRADING_START.minute, 
                                 second=0, microsecond=0)
            time_until = start_dt - dt_moscow
            time_info['status'] = 'before_open'
            time_info['time_until_event'] = str(time_until).split('.')[0]
            time_info['next_event'] = 'открытие'
        elif current_time_moscow > TradingRestrictions.TRADING_END:
            # После закрытия
            next_day = dt_moscow + timedelta(days=1)
            start_dt = next_day.replace(hour=TradingRestrictions.TRADING_START.hour,
                                       minute=TradingRestrictions.TRADING_START.minute,
                                       second=0, microsecond=0)
            time_until = start_dt - dt_moscow
            time_info['status'] = 'after_close'
            time_info['time_until_event'] = str(time_until).split('.')[0]
            time_info['next_event'] = 'открытие'
        else:
            # Во время торговой сессии
            end_dt = dt_moscow.replace(hour=TradingRestrictions.TRADING_END.hour,
                               minute=TradingRestrictions.TRADING_END.minute,
                               second=0, microsecond=0)
            time_until = end_dt - dt_moscow
            
            # Проверяем клиринговые окна
            in_clearing = False
            for start, end in TradingRestrictions.CLEARING_WINDOWS:
                if start <= current_time_moscow <= end:
                    in_clearing = True
                    clearing_end = dt_moscow.replace(hour=end.hour, minute=end.minute, 
                                            second=0, microsecond=0)
                    time_until_clearing_end = clearing_end - dt_moscow
                    time_info['status'] = 'clearing'
                    time_info['time_until_event'] = str(time_until_clearing_end).split('.')[0]
                    time_info['next_event'] = 'окончание клиринга'
                    break
            
            if not in_clearing:
                time_info['status'] = 'trading'
                time_info['time_until_event'] = str(time_until).split('.')[0]
                time_info['next_event'] = 'закрытие'
        
        return {
            'can_trade': can_trade,
            'reason': reason,
            'current_time': dt.strftime('%H:%M:%S'),
            'timezone': timezone_name,
            'trading_hours': f"{TradingRestrictions.TRADING_START.strftime('%H:%M')} - {TradingRestrictions.TRADING_END.strftime('%H:%M')} МСК",
            'status': time_info.get('status', 'unknown'),
            'time_until_event': time_info.get('time_until_event', 'N/A'),
            'next_event': time_info.get('next_event', 'N/A'),
            'is_weekend': dt_moscow.weekday() >= 5,
            'is_holiday': (dt_moscow.month, dt_moscow.day) in TradingRestrictions.HOLIDAYS
        }
