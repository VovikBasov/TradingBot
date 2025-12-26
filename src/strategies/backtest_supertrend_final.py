#!/usr/bin/env python3
"""
Исправленный бэктест стратегии Supertrend + MACD/RSI для GAZP
Теперь с корректным временем UTC+3 и выводом ключевых метрик
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from tinkoff.invest import AsyncClient, CandleInterval

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SupertrendBacktester:
    def __init__(self, token: str = None):
        if token is None:
            token = os.getenv('INVEST_TOKEN')
        if not token:
            raise ValueError("❌ Укажите INVEST_TOKEN в .env файле")
        
        self.token = token
        self.figi = "BBG004730RP0"
        
        # Параметры стратегии
        self.atr_period = 5
        self.supertrend_factor = 3.1
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.rsi_period = 13
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.stop_loss_pct = 1.0
        self.take_profit_pct = 5.0
        
        # Параметры бэктеста
        self.start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.initial_capital = 100000.0
        
        # Состояние
        self.capital = self.initial_capital
        self.position = 0.0
        self.position_avg_price = 0.0
        self.position_type = None
        self.position_entry_time = None
        self.current_trade = None
        
        # Результаты
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        
    def _quotation_to_float(self, quotation) -> float:
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def _convert_to_moscow_time(self, dt):
        """Конвертирует время из UTC в московское (UTC+3)"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=3)))
    
    async def fetch_candles(self) -> pd.DataFrame:
        """Загрузка часовых свечей за период"""
        logger.info(f"Загрузка данных с 01.01.2024 по 01.01.2025...")
        try:
            async with AsyncClient(self.token) as client:
                candles = []
                async for candle in client.get_all_candles(
                    figi=self.figi,
                    from_=self.start_date,
                    to=self.end_date,
                    interval=CandleInterval.CANDLE_INTERVAL_HOUR
                ):
                    # Конвертируем время из UTC в московское (UTC+3)
                    candle_time = self._convert_to_moscow_time(candle.time)
                    candles.append({
                        'time': candle_time,
                        'open': self._quotation_to_float(candle.open),
                        'high': self._quotation_to_float(candle.high),
                        'low': self._quotation_to_float(candle.low),
                        'close': self._quotation_to_float(candle.close),
                        'volume': candle.volume
                    })
                
                if not candles:
                    return pd.DataFrame()
                
                df = pd.DataFrame(candles)
                df.set_index('time', inplace=True)
                df.sort_index(inplace=True)
                logger.info(f"✅ Загружено {len(df)} часовых свечей (время в UTC+3)")
                return df
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            return pd.DataFrame()
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 5) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    def calculate_supertrend(self, df: pd.DataFrame) -> pd.DataFrame:
        atr = self.calculate_atr(df, self.atr_period)
        hl2 = (df['high'] + df['low']) / 2
        upper_band = hl2 + (self.supertrend_factor * atr)
        lower_band = hl2 - (self.supertrend_factor * atr)
        
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        
        for i in range(1, len(df)):
            close = df['close'].iloc[i]
            if i == 1:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
                continue
            
            prev_supertrend = supertrend.iloc[i-1]
            if prev_supertrend == upper_band.iloc[i-1]:
                if close > prev_supertrend:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = min(upper_band.iloc[i], prev_supertrend)
                    direction.iloc[i] = -1
            else:
                if close < prev_supertrend:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = max(lower_band.iloc[i], prev_supertrend)
                    direction.iloc[i] = 1
        
        return pd.DataFrame({'supertrend': supertrend, 'direction': direction})
    
    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        return pd.DataFrame({'macd_line': macd_line, 'signal_line': signal_line})
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 13) -> pd.Series:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) < 30:
            return df
        
        supertrend_df = self.calculate_supertrend(df)
        df['supertrend'] = supertrend_df['supertrend']
        df['supertrend_direction'] = supertrend_df['direction']
        
        macd_df = self.calculate_macd(df)
        df['macd_line'] = macd_df['macd_line']
        df['macd_signal'] = macd_df['signal_line']
        
        df['rsi'] = self.calculate_rsi(df, self.rsi_period)
        
        df['is_bullish_st'] = df['supertrend_direction'] == 1
        df['is_bearish_st'] = df['supertrend_direction'] == -1
        df['macd_bullish'] = df['macd_line'] > df['macd_signal']
        df['macd_bearish'] = df['macd_line'] < df['macd_signal']
        df['rsi_not_overbought'] = df['rsi'] < self.rsi_overbought
        df['rsi_not_oversold'] = df['rsi'] > self.rsi_oversold
        
        df['condition_pullback_long'] = (df['is_bullish_st'] & 
                                         (df['close'].shift(1) < df['supertrend'].shift(1)) & 
                                         (df['close'] > df['supertrend']))
        
        df['condition_pullback_short'] = (df['is_bearish_st'] & 
                                          (df['close'].shift(1) > df['supertrend'].shift(1)) & 
                                          (df['close'] < df['supertrend']))
        
        df['enter_long'] = (df['condition_pullback_long'] & df['macd_bullish'] & df['rsi_not_overbought'])
        df['enter_short'] = (df['condition_pullback_short'] & df['macd_bearish'] & df['rsi_not_oversold'])
        
        df['trend_reversal_to_bearish'] = (df['is_bearish_st'] & (df['supertrend_direction'].shift(1) != -1))
        df['trend_reversal_to_bullish'] = (df['is_bullish_st'] & (df['supertrend_direction'].shift(1) != 1))
        
        return df
    
    def execute_backtest(self, df: pd.DataFrame):
        logger.info("Запуск бэктеста...")
        df = self.calculate_all_indicators(df)
        
        if len(df) < 2:
            return
        
        # Конвертируем end_date в московское время для сравнения
        end_date_moscow = self._convert_to_moscow_time(self.end_date)
        
        for i in range(1, len(df)):
            current_row = df.iloc[i]
            current_time = df.index[i]  # Уже в UTC+3
            
            # Принудительное закрытие в конце периода
            if current_time >= end_date_moscow and self.position != 0:
                self.close_position(
                    price=current_row['close'],
                    time=current_time,
                    reason="Принудительное закрытие 01.01.2025"
                )
                continue
            
            # Выход по развороту тренда
            if self.position > 0 and current_row['trend_reversal_to_bearish']:
                self.close_position(
                    price=current_row['close'],
                    time=current_time,
                    reason="Выход: разворот Supertrend"
                )
            elif self.position < 0 and current_row['trend_reversal_to_bullish']:
                self.close_position(
                    price=current_row['close'],
                    time=current_time,
                    reason="Выход: разворот Supertrend"
                )
            
            # Выход по стоп-лоссу / тейк-профиту
            if self.position != 0 and self.position_avg_price > 0:
                if self.position_type == 'long':
                    stop_price = self.position_avg_price * (1 - self.stop_loss_pct/100)
                    take_price = self.position_avg_price * (1 + self.take_profit_pct/100)
                    if current_row['close'] <= stop_price:
                        self.close_position(
                            price=current_row['close'],
                            time=current_time,
                            reason="Стоп-лосс"
                        )
                    elif current_row['close'] >= take_price:
                        self.close_position(
                            price=current_row['close'],
                            time=current_time,
                            reason="Тейк-профит"
                        )
                else:  # short
                    stop_price = self.position_avg_price * (1 + self.stop_loss_pct/100)
                    take_price = self.position_avg_price * (1 - self.take_profit_pct/100)
                    if current_row['close'] >= stop_price:
                        self.close_position(
                            price=current_row['close'],
                            time=current_time,
                            reason="Стоп-лосс"
                        )
                    elif current_row['close'] <= take_price:
                        self.close_position(
                            price=current_row['close'],
                            time=current_time,
                            reason="Тейк-профит"
                        )
            
            # Вход в позицию
            if self.position == 0:
                if current_row['enter_long']:
                    self.enter_position(
                        price=current_row['close'],
                        time=current_time,
                        position_type='long',
                        reason="Вход в лонг"
                    )
                elif current_row['enter_short']:
                    self.enter_position(
                        price=current_row['close'],
                        time=current_time,
                        position_type='short',
                        reason="Вход в шорт"
                    )
            
            self.update_equity_curve(current_row['close'], current_time)
    
    def enter_position(self, price: float, time, position_type: str, reason: str):
        capital_to_use = self.capital
        quantity = capital_to_use / price
        
        lot_size = 10
        quantity = (quantity // lot_size) * lot_size
        
        if quantity < lot_size:
            return
        
        self.position = quantity if position_type == 'long' else -quantity
        self.position_avg_price = price
        self.position_type = position_type
        self.position_entry_time = time
        
        self.current_trade = {
            'entry_time': time,
            'exit_time': None,
            'position_type': position_type,
            'entry_price': price,
            'exit_price': None,
            'quantity': self.position,
            'entry_capital': self.capital,
            'exit_capital': None,
            'pnl': None,
            'pnl_pct': None,
            'reason_entry': reason,
            'reason_exit': None,
            'duration_hours': None
        }
        
        logger.info(f"⏰ {time.strftime('%d.%m.%Y %H:%M')} (UTC+3): {reason} по {price:.2f}")
    
    def close_position(self, price: float, time, reason: str):
        if self.position == 0 or self.current_trade is None:
            return
        
        if self.position_type == 'long':
            pnl = (price - self.position_avg_price) * abs(self.position)
            pnl_pct = ((price - self.position_avg_price) / self.position_avg_price) * 100
        else:
            pnl = (self.position_avg_price - price) * abs(self.position)
            pnl_pct = ((self.position_avg_price - price) / self.position_avg_price) * 100
        
        self.capital += pnl
        
        self.current_trade['exit_time'] = time
        self.current_trade['exit_price'] = price
        self.current_trade['exit_capital'] = self.capital
        self.current_trade['pnl'] = pnl
        self.current_trade['pnl_pct'] = pnl_pct
        self.current_trade['reason_exit'] = reason
        self.current_trade['duration_hours'] = (time - self.current_trade['entry_time']).total_seconds() / 3600
        
        self.trades.append(self.current_trade)
        
        if len(self.equity_curve) > 0:
            prev_equity = self.equity_curve[-1]['equity']
            current_equity = self.capital
            if prev_equity > 0:
                self.daily_returns.append((current_equity - prev_equity) / prev_equity)
        
        logger.info(f"⏰ {time.strftime('%d.%m.%Y %H:%M')} (UTC+3): {reason} по {price:.2f}, P&L: {pnl:+.2f} руб. ({pnl_pct:+.2f}%)")
        
        self.position = 0.0
        self.position_avg_price = 0.0
        self.position_type = None
        self.current_trade = None
    
    def update_equity_curve(self, current_price: float, time):
        position_value = 0.0
        if self.position > 0:
            position_value = (current_price - self.position_avg_price) * self.position
        elif self.position < 0:
            position_value = (self.position_avg_price - current_price) * abs(self.position)
        
        total_equity = self.capital + position_value
        
        if len(self.equity_curve) == 0 or time - self.equity_curve[-1]['time'] >= timedelta(hours=24):
            self.equity_curve.append({
                'time': time,
                'equity': total_equity,
                'capital': self.capital,
                'position_value': position_value,
                'price': current_price
            })
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Расчет всех метрик производительности"""
        if not self.equity_curve:
            return {}
        
        final_equity = self.equity_curve[-1]['equity']
        total_return_pct = (final_equity - self.initial_capital) / self.initial_capital * 100
        total_pnl = final_equity - self.initial_capital
        
        metrics = {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return_pct': total_return_pct,
            'total_pnl': total_pnl,
            'total_trades': len(self.trades),
        }
        
        # Статистика сделок
        if self.trades:
            winning_trades = [t for t in self.trades if t['pnl'] > 0]
            losing_trades = [t for t in self.trades if t['pnl'] < 0]
            
            win_rate = (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0
            total_win = sum(t['pnl'] for t in winning_trades)
            total_loss = sum(t['pnl'] for t in losing_trades)
            
            avg_win = total_win / len(winning_trades) if winning_trades else 0
            avg_loss = total_loss / len(losing_trades) if losing_trades else 0
            
            metrics.update({
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate_pct': win_rate,
                'total_win': total_win,
                'total_loss': total_loss,
                'profit_factor': abs(total_win / total_loss) if total_loss != 0 else float('inf'),
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'largest_win': max((t['pnl'] for t in self.trades), default=0),
                'largest_loss': min((t['pnl'] for t in self.trades), default=0),
            })
        
        # Коэффициенты Шарпа и Сортино
        if self.daily_returns:
            returns_series = pd.Series(self.daily_returns)
            annual_factor = np.sqrt(252)  # Годовой коэффициент
            
            # Коэффициент Шарпа (безрисковая ставка = 0)
            if returns_series.std() > 0:
                sharpe_ratio = annual_factor * returns_series.mean() / returns_series.std()
                metrics['sharpe_ratio'] = sharpe_ratio
            
            # Коэффициент Сортино (используем только отрицательные доходности)
            negative_returns = returns_series[returns_series < 0]
            if negative_returns.std() > 0:
                sortino_ratio = annual_factor * returns_series.mean() / negative_returns.std()
                metrics['sortino_ratio'] = sortino_ratio
        
        # Максимальная просадка
        if len(self.equity_curve) > 1:
            equities = [e['equity'] for e in self.equity_curve]
            cumulative = pd.Series(equities)
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown_pct = drawdown.min() * 100
            metrics['max_drawdown_pct'] = max_drawdown_pct
        
        return metrics
    
    def print_results(self, metrics: Dict[str, Any]):
        """Вывод результатов на экран"""
        print("\n" + "="*70)
        print("📊 РЕЗУЛЬТАТЫ БЭКТЕСТА STRATEGY SUPER TREND + MACD/RSI")
        print("="*70)
        
        print(f"\n📅 Период: 01.01.2024 - 01.01.2025")
        print(f"📈 Инструмент: GAZP | Таймфрейм: 1 час | Время: UTC+3")
        print(f"💰 Начальный капитал: {self.initial_capital:,.0f} руб.")
        
        print(f"\n" + "="*70)
        print("🎯 КЛЮЧЕВЫЕ МЕТРИКИ")
        print("="*70)
        
        # Ключевые метрики, которые запросил пользователь
        print(f"\n1️⃣  КОЛИЧЕСТВО СДЕЛОК: {metrics.get('total_trades', 0)}")
        
        print(f"\n2️⃣  ДОХОДНОСТЬ:")
        print(f"   Общая доходность:       {metrics.get('total_return_pct', 0):+.2f}%")
        print(f"   Конечный капитал:       {metrics.get('final_equity', 0):,.0f} руб.")
        print(f"   Общий P&L:              {metrics.get('total_pnl', 0):+,.0f} руб.")
        
        print(f"\n3️⃣  КОЭФФИЦИЕНТЫ РИСКА:")
        print(f"   Коэффициент Шарпа:      {metrics.get('sharpe_ratio', 0):.3f}")
        print(f"   Коэффициент Сортино:    {metrics.get('sortino_ratio', 0):.3f}")
        print(f"   Максимальная просадка:  {metrics.get('max_drawdown_pct', 0):.2f}%")
        
        print(f"\n" + "="*70)
        print("📈 ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА")
        print("="*70)
        
        print(f"\n📊 СТАТИСТИКА СДЕЛОК:")
        print(f"   Прибыльных сделок:      {metrics.get('winning_trades', 0)}")
        print(f"   Убыточных сделок:       {metrics.get('losing_trades', 0)}")
        print(f"   Процент успеха:         {metrics.get('win_rate_pct', 0):.1f}%")
        
        if 'avg_win' in metrics:
            print(f"   Средний выигрыш:        {metrics.get('avg_win', 0):.0f} руб.")
            print(f"   Средний проигрыш:       {metrics.get('avg_loss', 0):.0f} руб.")
            print(f"   Профит-фактор:          {metrics.get('profit_factor', 0):.2f}")
        
        print(f"\n⚙️  ПАРАМЕТРЫ СТРАТЕГИИ:")
        params = [
            ("ATR период", self.atr_period),
            ("Supertrend множитель", self.supertrend_factor),
            ("MACD", f"({self.macd_fast},{self.macd_slow},{self.macd_signal})"),
            ("RSI период", self.rsi_period),
            ("Стоп-лосс", f"{self.stop_loss_pct}%"),
            ("Тейк-профит", f"{self.take_profit_pct}%"),
            ("В сделку", "100% капитала")
        ]
        for name, value in params:
            print(f"   {name:<25} {value}")
        
        print(f"\n" + "="*70)
        
        # Краткая история сделок
        if self.trades:
            print(f"\n📋 ПОСЛЕДНИЕ 5 СДЕЛОК:")
            for i, trade in enumerate(self.trades[-5:]):
                idx = len(self.trades) - 5 + i + 1
                pnl_sign = '+' if trade['pnl'] > 0 else ''
                print(f"   {idx:3d}. {trade['entry_time'].strftime('%d.%m.%Y %H:%M')} → "
                      f"{trade['exit_time'].strftime('%d.%m.%Y %H:%M')}: "
                      f"{trade['position_type'].upper():5} | "
                      f"P&L: {pnl_sign}{trade['pnl']:.0f} руб. ({trade['pnl_pct']:+.1f}%) | "
                      f"Причина: {trade['reason_exit']}")
        
        print(f"\n" + "="*70)
        print("💡 Результаты также сохранены в backtest_results_final.json")
        print("="*70)
    
    def save_results(self, metrics: Dict[str, Any]):
        """Сохранение результатов в JSON файл"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'strategy': 'Supertrend + MACD/RSI',
            'period': '2024-01-01 to 2025-01-01',
            'timezone': 'UTC+3',
            'parameters': {
                'atr_period': self.atr_period,
                'supertrend_factor': self.supertrend_factor,
                'macd': f"{self.macd_fast},{self.macd_slow},{self.macd_signal}",
                'rsi_period': self.rsi_period,
                'stop_loss': f"{self.stop_loss_pct}%",
                'take_profit': f"{self.take_profit_pct}%",
            },
            'performance': {
                'initial_capital': self.initial_capital,
                'final_equity': metrics.get('final_equity', 0),
                'total_return_pct': metrics.get('total_return_pct', 0),
                'total_pnl': metrics.get('total_pnl', 0),
                'total_trades': metrics.get('total_trades', 0),
                'winning_trades': metrics.get('winning_trades', 0),
                'losing_trades': metrics.get('losing_trades', 0),
                'win_rate_pct': metrics.get('win_rate_pct', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'sortino_ratio': metrics.get('sortino_ratio', 0),
                'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
            },
            'trades': self.trades,
        }
        
        with open('backtest_results_final.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info("✅ Результаты сохранены в backtest_results_final.json")
    
    async def run(self):
        try:
            df = await self.fetch_candles()
            if df.empty:
                logger.error("Не удалось загрузить данные")
                return
            
            self.execute_backtest(df)
            
            # Принудительное закрытие в конце данных
            if self.position != 0 and len(df) > 0:
                last_price = df['close'].iloc[-1]
                last_time = df.index[-1]
                self.close_position(
                    price=last_price,
                    time=last_time,
                    reason="Принудительное закрытие в конце данных"
                )
            
            metrics = self.calculate_performance_metrics()
            if metrics:
                self.print_results(metrics)
                self.save_results(metrics)
            else:
                logger.error("Не удалось рассчитать метрики")
                
        except Exception as e:
            logger.error(f"Ошибка при выполнении бэктеста: {e}")
            import traceback
            logger.error(f"Подробности: {traceback.format_exc()}")

async def main():
    try:
        backtester = SupertrendBacktester()
    except ValueError as e:
        print(e)
        sys.exit(1)
    
    await backtester.run()

if __name__ == "__main__":
    asyncio.run(main())
