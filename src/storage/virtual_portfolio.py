import pandas as pd
from decimal import Decimal
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime
from src.utils.trading_restrictions import TradingRestrictions
from src.utils.slippage import SlippageSimulator
from src.utils.spread import SpreadCalculator
from src.utils.risk_manager import RiskManager
from src.analysis.performance_metrics import PerformanceMetrics
from src.config.trading_config import ACTIVE_CONFIG

class VirtualPortfolio:
    """
    Класс для управления виртуальным портфелем и отслеживания профита.
    Поддерживает работу с фьючерсами через маржинальную торговлю.
    
    Для фьючерсов:
    - При открытии позиции резервируется маржа (не вся стоимость контракта)
    - Баланс изменяется только при закрытии позиции (добавляется профит/убыток)
    - Отслеживается используемая маржа и свободные средства
    """
    def __init__(self, storage_path: str = "data/portfolio.json", client=None, config=None):
        self.storage_path = storage_path
        self.client = client  # T-Invest API клиент для получения информации о марже
        self.config = config or ACTIVE_CONFIG
        
        # Инициализация компонентов реалистичности
        slippage_cfg = self.config.SLIPPAGE_CONFIG
        self.slippage_simulator = SlippageSimulator(
            base_slippage_percent=slippage_cfg['base_slippage_percent'],
            volume_factor_per_10_lots=slippage_cfg['volume_factor_per_10_lots'],
            volatility_multiplier=slippage_cfg['volatility_multiplier'],
            max_slippage_percent=slippage_cfg['max_slippage_percent']
        ) if slippage_cfg['enabled'] else None
        
        spread_cfg = self.config.SPREAD_CONFIG
        self.spread_calculator = SpreadCalculator(
            base_spread_percent=spread_cfg['base_spread_percent'],
            volatility_multiplier=spread_cfg['volatility_multiplier'],
            min_spread_percent=spread_cfg['min_spread_percent'],
            max_spread_percent=spread_cfg['max_spread_percent']
        ) if spread_cfg['enabled'] else None
        
        risk_cfg = self.config.RISK_CONFIG
        self.risk_manager = RiskManager(
            max_drawdown_percent=risk_cfg['max_drawdown_percent'],
            risk_per_trade_percent=risk_cfg['risk_per_trade_percent'],
            max_open_positions=risk_cfg['max_open_positions'],
            daily_loss_limit_percent=risk_cfg['daily_loss_limit_percent'],
            max_position_size_percent=risk_cfg['max_position_size_percent']
        ) if risk_cfg['enabled'] else None
        
        metrics_cfg = self.config.METRICS_CONFIG
        self.performance_metrics = PerformanceMetrics(
            risk_free_rate=metrics_cfg['risk_free_rate']
        ) if metrics_cfg['enabled'] else None
        
        self.data = {
            "balance": Decimal(str(self.config.GENERAL_CONFIG['initial_balance'])),
            "initial_balance": Decimal(str(self.config.GENERAL_CONFIG['initial_balance'])),
            "positions": {},
            "history": [],
            "used_margin": Decimal("0"),
            "total_commission": Decimal("0"),
            "total_slippage_cost": Decimal("0"),
            "total_spread_cost": Decimal("0"),
            "next_trade_id": 1,
            "balance_history": [],
            "atr_history": {}  # ticker: [atr_values]
        }
        self.commission_rate = Decimal(str(self.config.GENERAL_CONFIG['commission_rate']))
        self._load()

    def _load(self):
        """Загружает состояние портфеля из файла."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    self.data["balance"] = Decimal(str(raw_data.get("balance", "200000.0")))
                    self.data["positions"] = {
                        k: {
                            "lots": v["lots"], 
                            "avg_price": Decimal(str(v["avg_price"])),
                            "stop_loss": Decimal(str(v.get("stop_loss", "0"))) if v.get("stop_loss") else None,
                            "take_profit": Decimal(str(v.get("take_profit", "0"))) if v.get("take_profit") else None,
                            "margin": Decimal(str(v.get("margin", "0"))),
                            "trade_id": v.get("trade_id"),
                            "opened_at": v.get("opened_at"),
                            "accumulated_commission": Decimal(str(v.get("accumulated_commission", "0")))
                        }
                        for k, v in raw_data.get("positions", {}).items()
                    }
                    self.data["history"] = raw_data.get("history", [])
                    self.data["used_margin"] = Decimal(str(raw_data.get("used_margin", "0")))
                    self.data["total_commission"] = Decimal(str(raw_data.get("total_commission", "0")))
                    self.data["total_slippage_cost"] = Decimal(str(raw_data.get("total_slippage_cost", "0")))
                    self.data["total_spread_cost"] = Decimal(str(raw_data.get("total_spread_cost", "0")))
                    self.data["next_trade_id"] = raw_data.get("next_trade_id", 1)
                    self.data["initial_balance"] = Decimal(str(raw_data.get("initial_balance", "200000.0")))
                    self.data["balance_history"] = raw_data.get("balance_history", [])
                    self.data["atr_history"] = raw_data.get("atr_history", {})
            except Exception as e:
                print(f"Ошибка при загрузке портфеля: {e}")
                self._save()  # Создаем новый файл с дефолтными значениями
        else:
            # Файл не существует - создаем новый
            print(f"Файл {self.storage_path} не найден. Создаем новый портфель с начальным балансом 200,000 ₽")
            self._save()

    def _save(self):
        """Сохраняет состояние портфеля в файл."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        serializable_data = {
            "balance": str(self.data["balance"]),
            "positions": {
                k: {
                    "lots": v["lots"],
                    "avg_price": str(v["avg_price"]),
                    "stop_loss": str(v["stop_loss"]) if v.get("stop_loss") else None,
                    "take_profit": str(v["take_profit"]) if v.get("take_profit") else None,
                    "margin": str(v.get("margin", "0")),
                    "trade_id": v.get("trade_id"),
                    "opened_at": v.get("opened_at"),
                    "accumulated_commission": str(v.get("accumulated_commission", "0"))
                }
                for k, v in self.data["positions"].items()
            },
            "history": self.data["history"],
            "used_margin": str(self.data["used_margin"]),
            "total_commission": str(self.data["total_commission"]),
            "total_slippage_cost": str(self.data.get("total_slippage_cost", "0")),
            "total_spread_cost": str(self.data.get("total_spread_cost", "0")),
            "next_trade_id": self.data["next_trade_id"],
            "initial_balance": str(self.data.get("initial_balance", "200000.0")),
            "balance_history": self.data.get("balance_history", []),
            "atr_history": self.data.get("atr_history", {})
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=4, ensure_ascii=False)

    def _calculate_execution_price(self, ticker: str, expected_price: Decimal, lots: int, 
                                   direction: str, atr: float = None) -> Decimal:
        """
        Рассчитывает реалистичную цену исполнения с учетом проскальзывания и спреда.
        
        Args:
            ticker: Тикер инструмента
            expected_price: Ожидаемая цена
            lots: Количество лотов
            direction: Направление ('buy' или 'sell')
            atr: Текущий ATR для учета волатильности
            
        Returns:
            Фактическая цена исполнения
        """
        execution_price = expected_price
        
        # Получаем средний ATR для сравнения
        avg_atr = None
        if atr and ticker in self.data["atr_history"]:
            atr_list = self.data["atr_history"][ticker]
            if atr_list:
                avg_atr = sum(atr_list) / len(atr_list)
        
        # Применяем спред bid/ask
        if self.spread_calculator:
            execution_price = self.spread_calculator.get_execution_price(
                mid_price=expected_price,
                direction=direction,
                atr=atr,
                avg_atr=avg_atr
            )
            spread_cost = abs(execution_price - expected_price) * Decimal(str(abs(lots)))
            self.data["total_spread_cost"] += spread_cost
        
        # Применяем проскальзывание
        if self.slippage_simulator:
            execution_price = self.slippage_simulator.calculate_slippage(
                expected_price=execution_price,
                lots=abs(lots),
                direction=direction,
                atr=atr,
                avg_atr=avg_atr
            )
            slippage_cost = abs(execution_price - expected_price) * Decimal(str(abs(lots)))
            self.data["total_slippage_cost"] += slippage_cost
        
        return execution_price
    
    def _update_atr_history(self, ticker: str, atr: float, max_history: int = 100):
        """
        Обновляет историю ATR для инструмента.
        
        Args:
            ticker: Тикер инструмента
            atr: Значение ATR
            max_history: Максимальная длина истории
        """
        if ticker not in self.data["atr_history"]:
            self.data["atr_history"][ticker] = []
        
        self.data["atr_history"][ticker].append(atr)
        
        # Ограничиваем размер истории
        if len(self.data["atr_history"][ticker]) > max_history:
            self.data["atr_history"][ticker] = self.data["atr_history"][ticker][-max_history:]
    
    def update_position(self, ticker: str, target_lots: int, current_price: Decimal, 
                       stop_loss: Decimal = None, take_profit: Decimal = None,
                       figi: str = None, margin_per_lot: Decimal = None, atr: float = None):
        """
        Обновляет позицию по тикеру до целевого количества лотов.
        Теперь с реалистичным исполнением: проскальзывание, спред, риск-менеджмент.
        
        Args:
            ticker: Тикер инструмента
            target_lots: Целевое количество лотов (отрицательное для long, положительное для short)
            current_price: Текущая цена
            stop_loss: Уровень стоп-лосса
            take_profit: Уровень тейк-профита
            figi: FIGI инструмента (для получения маржи через API)
            margin_per_lot: Маржа на 1 лот (если None, используется упрощенный расчет)
            atr: Текущий ATR для расчета проскальзывания и спреда
        """
        current_pos = self.data["positions"].get(ticker, {
            "lots": 0, 
            "avg_price": Decimal("0"), 
            "stop_loss": None, 
            "take_profit": None,
            "margin": Decimal("0"),
            "trade_id": None,
            "accumulated_commission": Decimal("0")
        })
        diff_lots = target_lots - current_pos["lots"]

        if diff_lots == 0:
            return
        
        # Проверка торговых ограничений
        can_trade, trade_reason = TradingRestrictions.can_trade()
        if not can_trade:
            print(f"⚠️  Торговля запрещена: {trade_reason}")
            return
        
        # Проверка минимального размера позиции
        is_valid_size, size_reason = TradingRestrictions.validate_position_size(target_lots)
        if not is_valid_size:
            print(f"⚠️  Недопустимый размер позиции: {size_reason}")
            return

        # Обновляем историю ATR
        if atr:
            self._update_atr_history(ticker, atr)
        
        # Проверка риск-менеджмента перед открытием новой позиции
        if target_lots != 0 and self.risk_manager:
            current_positions_count = len(self.data["positions"])
            position_value = abs(current_price * Decimal(str(abs(target_lots))))
            
            can_open, risk_reason = self.risk_manager.can_open_position(
                current_balance=self.data["balance"],
                current_positions=current_positions_count,
                position_value=position_value
            )
            
            if not can_open:
                print(f"🛑 Риск-менеджмент: {risk_reason}")
                return
        
        if target_lots == 0:
            # Полное закрытие позиции
            # Определяем направление для расчета цены исполнения
            direction = 'sell' if current_pos["lots"] < 0 else 'buy'
            
            # Рассчитываем реалистичную цену закрытия
            execution_price = self._calculate_execution_price(
                ticker=ticker,
                expected_price=current_price,
                lots=current_pos["lots"],
                direction=direction,
                atr=atr
            )
            
            profit = (execution_price - current_pos["avg_price"]) * Decimal(str(current_pos["lots"]))
            
            # Рассчитываем комиссию за закрытие
            turnover = abs(execution_price * Decimal(str(current_pos["lots"])))
            commission = turnover * self.commission_rate
            
            # Освобождаем маржу и добавляем профит к балансу (минус комиссия)
            released_margin = current_pos.get("margin", Decimal("0"))
            net_profit = profit - commission
            self.data["balance"] += released_margin + net_profit
            self.data["used_margin"] -= released_margin
            self.data["total_commission"] += commission
            
            trade_id = current_pos.get("trade_id")
            # Обновляем историю баланса для метрик
            self.data["balance_history"].append(float(self.data["balance"]))
            
            self.data["history"].append({
                "trade_id": trade_id,
                "ticker": ticker,
                "action": "close",
                "lots": current_pos["lots"],
                "expected_price": str(current_price),
                "execution_price": str(execution_price),
                "price": str(execution_price),
                "profit": str(profit),
                "commission": str(commission),
                "net_profit": str(net_profit),
                "margin_released": str(released_margin),
                "opened_at": current_pos.get("opened_at"),
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            if ticker in self.data["positions"]:
                del self.data["positions"][ticker]
        else:
            # Открытие или изменение позиции
            # Определяем направление для расчета цены исполнения
            direction = 'buy' if target_lots < 0 else 'sell'
            
            # Рассчитываем реалистичную цену открытия
            execution_price = self._calculate_execution_price(
                ticker=ticker,
                expected_price=current_price,
                lots=target_lots,
                direction=direction,
                atr=atr
            )
            
            # Рассчитываем требуемую маржу
            if margin_per_lot is None:
                # Упрощенный расчет: 10% от стоимости позиции
                margin_per_lot = execution_price * Decimal("0.1")
            
            required_margin = margin_per_lot * Decimal(abs(target_lots))
            
            # Проверяем достаточность средств
            available_balance = self.data["balance"] - self.data["used_margin"]
            if required_margin > available_balance:
                print(f"Недостаточно средств для открытия позиции. Требуется: {required_margin}, Доступно: {available_balance}")
                return
            
            # Рассчитываем комиссию за открытие/изменение
            turnover = abs(execution_price * Decimal(str(abs(diff_lots))))
            commission = turnover * self.commission_rate
            
            # Резервируем маржу и вычитаем комиссию
            old_margin = current_pos.get("margin", Decimal("0"))
            margin_diff = required_margin - old_margin
            
            self.data["balance"] -= (margin_diff + commission)
            self.data["used_margin"] += margin_diff
            self.data["total_commission"] += commission
            
            # Получаем или создаем trade_id
            trade_id = current_pos.get("trade_id")
            if trade_id is None:
                # Новая сделка - генерируем новый ID
                trade_id = self.data["next_trade_id"]
                self.data["next_trade_id"] += 1
            
            # Сохраняем время открытия только для новых сделок
            opened_at = current_pos.get("opened_at")
            if opened_at is None:
                opened_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Накапливаем комиссию для этой позиции
            accumulated_commission = current_pos.get("accumulated_commission", Decimal("0")) + commission
            
            self.data["positions"][ticker] = {
                "lots": target_lots,
                "avg_price": execution_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "margin": required_margin,
                "trade_id": trade_id,
                "opened_at": opened_at,
                "accumulated_commission": accumulated_commission
            }
            self.data["history"].append({
                "trade_id": trade_id,
                "ticker": ticker,
                "action": "update",
                "lots": target_lots,
                "expected_price": str(current_price),
                "execution_price": str(execution_price),
                "price": str(execution_price),
                "stop_loss": str(stop_loss) if stop_loss else None,
                "take_profit": str(take_profit) if take_profit else None,
                "margin_reserved": str(required_margin),
                "commission": str(commission),
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        self._save()

    def get_portfolio_summary(self, current_prices: Dict[str, Decimal] = None) -> Dict[str, Any]:
        """
        Возвращает сводку по портфелю.
        balance - свободные деньги (начальный баланс + реализованный профит)
        unrealized_pnl - нереализованная прибыль/убыток по открытым позициям
        total_value - баланс + нереализованный P&L
        """
        if current_prices is None:
            current_prices = {}
            
        unrealized_pnl = Decimal("0")
        pos_details = []
        
        for ticker, pos in self.data["positions"].items():
            # Используем текущую цену если есть, иначе цену входа
            current_price = current_prices.get(ticker, pos["avg_price"])
            
            # Расчет нереализованного P&L для позиции
            position_pnl = (current_price - pos["avg_price"]) * Decimal(str(pos["lots"]))
            unrealized_pnl += position_pnl
            
            pos_details.append({
                "ticker": ticker,
                "lots": pos["lots"],
                "entry_price": pos["avg_price"],
                "current_price": current_price,
                "unrealized_pnl": position_pnl
            })

        # Обновляем пиковый баланс для риск-менеджмента
        if self.risk_manager:
            self.risk_manager.update_peak_balance(self.data["balance"])
        
        return {
            "balance": self.data["balance"],
            "initial_balance": self.data.get("initial_balance", Decimal("200000.0")),
            "used_margin": self.data["used_margin"],
            "free_balance": self.data["balance"] - self.data["used_margin"],
            "unrealized_pnl": unrealized_pnl,
            "total_value": self.data["balance"] + unrealized_pnl,
            "total_commission": self.data.get("total_commission", Decimal("0")),
            "total_slippage_cost": self.data.get("total_slippage_cost", Decimal("0")),
            "total_spread_cost": self.data.get("total_spread_cost", Decimal("0")),
            "positions": pos_details
        }
    
    def check_stop_loss_take_profit(self, ticker: str, current_price: Decimal) -> str:
        """
        Проверяет, достигнут ли стоп-лосс или тейк-профит для открытой позиции.
        Возвращает: 'stop_loss', 'take_profit' или None
        """
        if ticker not in self.data["positions"]:
            return None
        
        pos = self.data["positions"][ticker]
        
        # Для long позиций (отрицательные лоты)
        if pos["lots"] < 0:
            if pos["stop_loss"] and current_price <= pos["stop_loss"]:
                return 'stop_loss'
            if pos["take_profit"] and current_price >= pos["take_profit"]:
                return 'take_profit'
        
        # Для short позиций (положительные лоты)
        elif pos["lots"] > 0:
            if pos["stop_loss"] and current_price >= pos["stop_loss"]:
                return 'stop_loss'
            if pos["take_profit"] and current_price <= pos["take_profit"]:
                return 'take_profit'
        
        return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Возвращает метрики производительности торговой стратегии.
        
        Returns:
            Словарь с метриками производительности
        """
        if not self.performance_metrics:
            return {"error": "Метрики отключены в конфигурации"}
        
        initial_balance = float(self.data.get("initial_balance", Decimal("200000.0")))
        balance_history = self.data.get("balance_history", [])
        
        # Добавляем текущий баланс если его еще нет
        if not balance_history or balance_history[-1] != float(self.data["balance"]):
            balance_history = balance_history + [float(self.data["balance"])]
        
        # Рассчитываем все метрики
        metrics = self.performance_metrics.calculate_all_metrics(
            balance_history=balance_history,
            trades=self.data["history"],
            initial_balance=initial_balance
        )
        
        # Добавляем информацию о риск-менеджменте
        if self.risk_manager:
            risk_status = self.risk_manager.get_risk_status(
                current_balance=self.data["balance"],
                current_positions=len(self.data["positions"])
            )
            metrics["risk_management"] = risk_status
        
        # Добавляем информацию о затратах
        metrics["costs"] = {
            "total_commission": float(self.data.get("total_commission", Decimal("0"))),
            "total_slippage_cost": float(self.data.get("total_slippage_cost", Decimal("0"))),
            "total_spread_cost": float(self.data.get("total_spread_cost", Decimal("0"))),
            "total_costs": float(
                self.data.get("total_commission", Decimal("0")) +
                self.data.get("total_slippage_cost", Decimal("0")) +
                self.data.get("total_spread_cost", Decimal("0"))
            )
        }
        
        return metrics
