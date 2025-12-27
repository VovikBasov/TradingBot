#!/usr/bin/env python3
"""
Финальный бэктест стратегии Supertrend + MACD/RSI для GAZP.
Синхронизирован с TradingView: ATR рассчитан методом RMA, исправлена логика Supertrend.
Период: 01.01.2024 - 01.01.2025.
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

import talib
import ta

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

        # Параметры стратегии (оставлены как есть)
        self.atr_period = 5
        self.supertrend_factor = 3.1
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.rsi_period = 13
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.stop_loss_pct = 2.0
        self.take_profit_pct = 4.0

        # Параметры бэктеста: 01.01.2024 - 01.01.2025
        self.start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.initial_capital = 100000.0

        self.capital = self.initial_capital
        self.position = 0.0
        self.position_avg_price = 0.0
        self.position_type = None
        self.position_entry_time = None
        self.current_trade = None

        self.trades = []
        self.equity_curve = []
        self.daily_returns = []

    def _quotation_to_float(self, quotation) -> float:
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0

    def _convert_to_moscow_time(self, dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=3)))

    async def fetch_candles(self) -> pd.DataFrame:
        """Загрузка часовых свечей за период 2024 года."""
        logger.info(f"Загрузка данных с {self.start_date.date()} по {self.end_date.date()}...")
        try:
            async with AsyncClient(self.token) as client:
                candles = []
                async for candle in client.get_all_candles(
                    figi=self.figi,
                    from_=self.start_date,
                    to=self.end_date,
                    interval=CandleInterval.CANDLE_INTERVAL_HOUR
                ):
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
                logger.info(f"✅ Загружено {len(df)} часовых свечей (UTC+3)")
                return df
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            return pd.DataFrame()

    def calculate_atr_rma(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Расчёт ATR методом RMA (Wilder's Moving Average), как в TradingView.
        RMA - это экспоненциальное среднее с alpha = 1/period.
        """
        # 1. Рассчитываем True Range (TR)
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (prev_close - df['low']).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 2. Рассчитываем RMA: первое значение - SMA, далее - RMA
        atr_rma = tr.copy()
        # Инициализация первым значением SMA
        atr_rma.iloc[:period] = tr.iloc[:period].mean()
        # Рекурсивный расчёт RMA для остальных значений
        for i in range(period, len(tr)):
            atr_rma.iloc[i] = (atr_rma.iloc[i-1] * (period - 1) + tr.iloc[i]) / period
        return atr_rma

    def calculate_supertrend(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ручной расчёт Supertrend с использованием ATR (RMA).
        Логика направления и рекурсивных полос исправлена в соответствии с TradingView.
        """
        # Используем ATR RMA
        atr = self.calculate_atr_rma(df, self.atr_period)
        hl2 = (df['high'] + df['low']) / 2

        # Базовые полосы
        basic_upper = hl2 + (self.supertrend_factor * atr)
        basic_lower = hl2 - (self.supertrend_factor * atr)

        # Инициализация массивов для финальных полос
        final_upper = basic_upper.copy().values
        final_lower = basic_lower.copy().values
        supertrend = np.zeros(len(df))
        direction = np.zeros(len(df))  # 1 = бычий, -1 = медвежий (наша внутренняя логика)

        # Инициализация первого значения
        supertrend[0] = basic_upper.iloc[0]
        direction[0] = -1  # Первое значение медвежье

        # Рекурсивный расчёт для остальных баров
        for i in range(1, len(df)):
            # Финальная верхняя полоса (с учётом предыдущего значения и условия по close[1])
            if (basic_upper.iloc[i] < final_upper[i-1]) or (df['close'].iloc[i-1] > final_upper[i-1]):
                final_upper[i] = basic_upper.iloc[i]
            else:
                final_upper[i] = final_upper[i-1]

            # Финальная нижняя полоса (с учётом предыдущего значения и условия по close[1])
            if (basic_lower.iloc[i] > final_lower[i-1]) or (df['close'].iloc[i-1] < final_lower[i-1]):
                final_lower[i] = basic_lower.iloc[i]
            else:
                final_lower[i] = final_lower[i-1]

            # Определение Supertrend и направления
            if supertrend[i-1] == final_upper[i-1]:
                if df['close'].iloc[i] <= final_upper[i]:
                    supertrend[i] = final_upper[i]
                    direction[i] = -1  # Медвежий
                else:
                    supertrend[i] = final_lower[i]
                    direction[i] = 1   # Бычий
            else:  # supertrend[i-1] == final_lower[i-1]
                if df['close'].iloc[i] >= final_lower[i]:
                    supertrend[i] = final_lower[i]
                    direction[i] = 1   # Бычий
                else:
                    supertrend[i] = final_upper[i]
                    direction[i] = -1  # Медвежий

        # Преобразование направления в логику TradingView: direction < 0 = бычий, direction > 0 = медвежий
        direction_tv = np.where(direction == 1, -1, 1)

        return pd.DataFrame({
            'supertrend': supertrend,
            'direction': direction_tv,
            'is_bullish_st': direction_tv < 0,  # Бычий тренд в TV
            'is_bearish_st': direction_tv > 0   # Медвежий тренд в TV
        }, index=df.index)

    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Расчёт MACD с использованием TA-Lib."""
        macd_line, signal_line, _ = talib.MACD(df['close'].values,
                                               fastperiod=self.macd_fast,
                                               slowperiod=self.macd_slow,
                                               signalperiod=self.macd_signal)
        return pd.DataFrame({
            'macd_line': macd_line,
            'signal_line': signal_line,
            'macd_bullish': macd_line > signal_line,
            'macd_bearish': macd_line < signal_line
        }, index=df.index)

    def calculate_rsi(self, df: pd.DataFrame, period: int = 13) -> pd.Series:
        """Расчёт RSI с использованием TA-Lib."""
        rsi_values = talib.RSI(df['close'].values, timeperiod=period)
        return pd.Series(rsi_values, index=df.index)

    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) < 30:
            return df

        supertrend_df = self.calculate_supertrend(df)
        df['supertrend'] = supertrend_df['supertrend']
        df['supertrend_direction'] = supertrend_df['direction']
        df['is_bullish_st'] = supertrend_df['is_bullish_st']
        df['is_bearish_st'] = supertrend_df['is_bearish_st']

        macd_df = self.calculate_macd(df)
        df['macd_line'] = macd_df['macd_line']
        df['macd_signal'] = macd_df['signal_line']
        df['macd_bullish'] = macd_df['macd_bullish']
        df['macd_bearish'] = macd_df['macd_bearish']

        df['rsi'] = self.calculate_rsi(df, self.rsi_period)
        df['rsi_not_overbought'] = df['rsi'] < self.rsi_overbought
        df['rsi_not_oversold'] = df['rsi'] > self.rsi_oversold

        # Условия входа по откату (как в TradingView)
        df['condition_pullback_long'] = (
            df['is_bullish_st'] &
            (df['close'].shift(1) < df['supertrend'].shift(1)) &
            (df['close'] > df['supertrend'])
        )
        df['condition_pullback_short'] = (
            df['is_bearish_st'] &
            (df['close'].shift(1) > df['supertrend'].shift(1)) &
            (df['close'] < df['supertrend'])
        )

        df['enter_long'] = (
            df['condition_pullback_long'] &
            df['macd_bullish'] &
            df['rsi_not_overbought']
        )
        df['enter_short'] = (
            df['condition_pullback_short'] &
            df['macd_bearish'] &
            df['rsi_not_oversold']
        )

        # Сигналы выхода по развороту Supertrend
        df['trend_reversal_to_bearish'] = (
            df['is_bearish_st'] &
            (~df['is_bearish_st'].shift(1).fillna(False))
        )
        df['trend_reversal_to_bullish'] = (
            df['is_bullish_st'] &
            (~df['is_bullish_st'].shift(1).fillna(False))
        )

        return df

    def execute_backtest(self, df: pd.DataFrame):
        logger.info("Запуск финального бэктеста...")
        df = self.calculate_all_indicators(df)

        if len(df) < 2:
            return

        end_date_moscow = self._convert_to_moscow_time(self.end_date)

        for i in range(1, len(df)):
            current_row = df.iloc[i]
            current_time = df.index[i]

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
                else:
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
        """Управление капиталом: 100% реинвестирование (как в TradingView)."""
        capital_to_use = self.capital
        quantity = capital_to_use / price

        lot_size = 10
        quantity = (quantity // lot_size) * lot_size

        if quantity < lot_size:
            logger.warning(f"Недостаточно капитала для покупки хотя бы 1 лота.")
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

        logger.info(f"⏰ {time.strftime('%d.%m.%Y %H:%M')} (UTC+3): {reason} по {price:.2f}, Кол-во: {abs(quantity):.0f}")

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

        logger.info(f"⏰ {time.strftime('%d.%m.%Y %H:%M')} (UTC+3): {reason} по {price:.2f}, P&L: {pnl:+.2f} руб. ({pnl_pct:+.2f}%), Капитал: {self.capital:.2f}")

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

        if self.daily_returns:
            returns_series = pd.Series(self.daily_returns)
            annual_factor = np.sqrt(252)

            if returns_series.std() > 0:
                sharpe_ratio = annual_factor * returns_series.mean() / returns_series.std()
                metrics['sharpe_ratio'] = sharpe_ratio

            negative_returns = returns_series[returns_series < 0]
            if negative_returns.std() > 0:
                sortino_ratio = annual_factor * returns_series.mean() / negative_returns.std()
                metrics['sortino_ratio'] = sortino_ratio

        if len(self.equity_curve) > 1:
            equities = [e['equity'] for e in self.equity_curve]
            cumulative = pd.Series(equities)
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown_pct = drawdown.min() * 100
            metrics['max_drawdown_pct'] = max_drawdown_pct

        return metrics

    def print_results(self, metrics: Dict[str, Any]):
        print("\n" + "="*70)
        print("📊 РЕЗУЛЬТАТЫ ФИНАЛЬНОГО БЭКТЕСТА (с исправлениями ATR RMA)")
        print("="*70)

        print(f"\n📅 Период: 01.01.2024 - 01.01.2025 | Таймфрейм: 1 час")
        print(f"📈 Инструмент: GAZP | Управление капиталом: Реинвестирование 100%")
        print(f"💰 Начальный капитал: {self.initial_capital:,.0f} руб.")

        print(f"\n🎯 КЛЮЧЕВЫЕ МЕТРИКИ")
        print(f"1️⃣  КОЛИЧЕСТВО СДЕЛОК: {metrics.get('total_trades', 0)}")
        print(f"2️⃣  ОБЩАЯ ДОХОДНОСТЬ: {metrics.get('total_return_pct', 0):+.2f}%")
        print(f"3️⃣  КОНЕЧНЫЙ КАПИТАЛ: {metrics.get('final_equity', 0):,.0f} руб.")
        print(f"4️⃣  КОЭФФИЦИЕНТ ШАРПА: {metrics.get('sharpe_ratio', 0):.3f}")
        print(f"5️⃣  МАКС. ПРОСАДКА: {metrics.get('max_drawdown_pct', 0):.2f}%")

        print(f"\n⚙️  ОСОБЕННОСТИ РЕАЛИЗАЦИИ:")
        print(f"   - ATR рассчитан методом RMA (Wilder's), как в TradingView")
        print(f"   - Supertrend: ручная реализация с исправленной рекурсивной логикой")
        print(f"   - MACD/RSI: рассчитаны с помощью TA-Lib")

        if self.trades:
            print(f"\n📋 ПОСЛЕДНИЕ 5 СДЕЛОК:")
            for i, trade in enumerate(self.trades[-5:]):
                idx = len(self.trades) - 5 + i + 1
                pnl_sign = '+' if trade['pnl'] > 0 else ''
                print(f"   {idx:3d}. {trade['entry_time'].strftime('%d.%m.%Y %H:%M')} → "
                      f"{trade['exit_time'].strftime('%d.%m.%Y %H:%M')}: "
                      f"{trade['position_type'].upper():5} | "
                      f"P&L: {pnl_sign}{trade['pnl']:.0f} руб. ({trade['pnl_pct']:+.1f}%)")

        print(f"\n" + "="*70)

    def save_results(self, metrics: Dict[str, Any]):
        results = {
            'timestamp': datetime.now().isoformat(),
            'strategy': 'Supertrend + MACD/RSI (ATR RMA исправление)',
            'period': '2024-01-01 to 2025-01-01',
            'timeframe': '1 hour',
            'parameters': {
                'atr_period': self.atr_period,
                'supertrend_factor': self.supertrend_factor,
                'macd': f"{self.macd_fast},{self.macd_slow},{self.macd_signal}",
                'rsi_period': self.rsi_period,
                'stop_loss': f"{self.stop_loss_pct}%",
                'take_profit': f"{self.take_profit_pct}%",
            },
            'performance': metrics,
            'trades': self.trades,
        }

        with open('backtest_results_final_rma.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        logger.info("✅ Результаты сохранены в backtest_results_final_rma.json")

    async def run(self):
        try:
            df = await self.fetch_candles()
            if df.empty:
                logger.error("Не удалось загрузить данные")
                return

            self.execute_backtest(df)

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
