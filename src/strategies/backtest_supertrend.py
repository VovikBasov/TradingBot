#!/usr/bin/env python3
"""
Бэктест стратегии Supertrend + MACD/RSI для GAZP
Период: 2024-01-01 - 2025-01-01
Таймфрейм: 1 час
Все расчеты производятся локально, как в supertrend_scanner.py
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

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

from tinkoff.invest import AsyncClient, CandleInterval
from tinkoff.invest.utils import now

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SupertrendBacktester:
    """Бэктестер стратегии Supertrend + MACD/RSI"""
    
    def __init__(self, token: str = None):
        """Инициализация бэктестера"""
        if token is None:
            token = os.getenv('INVEST_TOKEN')
        
        if not token:
            logger.error("❌ Токен не найден. Укажите в .env файле как INVEST_TOKEN")
            raise ValueError("Токен Tinkoff API не найден")
        
        self.token = token
        self.figi = "BBG004730RP0"  # FIGI для GAZP
        
        # Параметры стратегии (ТОЧНО такие же как в supertrend_scanner.py)
        self.atr_period = 5
        self.supertrend_factor = 3.1
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.rsi_period = 13
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.stop_loss_perc = 1.0
        self.take_profit_perc = 5.0
        
        # Параметры бэктеста - используем UTC для единообразия
        self.start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.initial_capital = 100000.0
        self.position_size_pct = 1.0  # 100% капитала в сделку
        
        # Состояние бэктеста
        self.capital = self.initial_capital
        self.position = 0.0  # Количество акций
        self.position_avg_price = 0.0
        self.position_type = None  # 'long' или 'short'
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        
    def _quotation_to_float(self, quotation) -> float:
        """Конвертирует Quotation в float (как в рабочем скрипте)"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def _make_datetime_naive(self, dt):
        """Преобразует datetime к наивному формату (без часового пояса)"""
        if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    
    async def fetch_candles(self) -> pd.DataFrame:
        """Загрузка свечей за период бэктеста"""
        logger.info(f"Загрузка данных с {self.start_date.strftime('%d.%m.%Y')} по {self.end_date.strftime('%d.%m.%Y')}...")
        
        try:
            async with AsyncClient(self.token) as client:
                candles = []
                async for candle in client.get_all_candles(
                    figi=self.figi,
                    from_=self.start_date,
                    to=self.end_date,
                    interval=CandleInterval.CANDLE_INTERVAL_HOUR
                ):
                    # Преобразуем время к наивному datetime для единообразия
                    candle_time = candle.time
                    if hasattr(candle_time, 'tzinfo') and candle_time.tzinfo is not None:
                        candle_time = candle_time.replace(tzinfo=None)
                    
                    candles.append({
                        'time': candle_time,
                        'open': self._quotation_to_float(candle.open),
                        'high': self._quotation_to_float(candle.high),
                        'low': self._quotation_to_float(candle.low),
                        'close': self._quotation_to_float(candle.close),
                        'volume': candle.volume
                    })
                
                if not candles:
                    logger.error("Не удалось получить свечи")
                    return pd.DataFrame()
                
                df = pd.DataFrame(candles)
                df.set_index('time', inplace=True)
                df.sort_index(inplace=True)
                
                logger.info(f"Загружено {len(df)} часовых свечей")
                return df
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")
            import traceback
            logger.error(f"Подробности: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 5) -> pd.Series:
        """Расчет Average True Range (ATR) - как в supertrend_scanner.py"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = true_range.max(axis=1)
        
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def calculate_supertrend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Расчет индикатора Supertrend - как в supertrend_scanner.py"""
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
                direction.iloc[i] = -1  # Медвежий
                continue
            
            prev_supertrend = supertrend.iloc[i-1]
            
            if prev_supertrend == upper_band.iloc[i-1]:
                if close > prev_supertrend:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1  # Бычий
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
        """Расчет индикатора MACD - как в supertrend_scanner.py"""
        ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram
        })
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 13) -> pd.Series:
        """Расчет индикатора RSI - как в supertrend_scanner.py"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Расчет всех индикаторов (ТОЧНО как в supertrend_scanner.py)"""
        if len(df) < 30:
            logger.warning(f"Мало данных: {len(df)} свечей. Нужно минимум 30 для расчетов.")
            return df
        
        # Расчет Supertrend
        supertrend_df = self.calculate_supertrend(df)
        df['supertrend'] = supertrend_df['supertrend']
        df['supertrend_direction'] = supertrend_df['direction']
        
        # Расчет MACD
        macd_df = self.calculate_macd(df)
        df['macd_line'] = macd_df['macd_line']
        df['macd_signal'] = macd_df['signal_line']
        
        # Расчет RSI
        rsi_series = self.calculate_rsi(df, self.rsi_period)
        df['rsi'] = rsi_series
        
        # Определяем условия (ТОЧНО как в analyze_signals из supertrend_scanner.py)
        df['is_bullish_st'] = df['supertrend_direction'] == 1
        df['is_bearish_st'] = df['supertrend_direction'] == -1
        
        # MACD условия
        df['macd_bullish'] = df['macd_line'] > df['macd_signal']
        df['macd_bearish'] = df['macd_line'] < df['macd_signal']
        
        # RSI условия
        df['rsi_not_overbought'] = df['rsi'] < self.rsi_overbought
        df['rsi_not_oversold'] = df['rsi'] > self.rsi_oversold
        
        # Условия отката (ТОЧНАЯ логика из PineScript)
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
        
        # Сигналы входа (ТОЧНО как в supertrend_scanner.py)
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
            (df['supertrend_direction'].shift(1) != -1)
        )
        
        df['trend_reversal_to_bullish'] = (
            df['is_bullish_st'] & 
            (df['supertrend_direction'].shift(1) != 1)
        )
        
        return df
    
    def execute_backtest(self, df: pd.DataFrame):
        """Выполнение бэктеста на исторических данных"""
        logger.info("Запуск бэктеста...")
        
        # Рассчитываем индикаторы
        df = self.calculate_all_indicators(df)
        
        if len(df) < 2:
            logger.error("Недостаточно данных после расчетов индикаторов")
            return
        
        # Преобразуем end_date к наивному datetime для сравнения
        end_date_naive = self._make_datetime_naive(self.end_date)
        
        # Проходим по всем свечам
        for i in range(1, len(df)):  # Начинаем с 1, чтобы иметь доступ к предыдущей свече
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            current_time = df.index[i]
            
            # Преобразуем current_time к наивному datetime для сравнения
            current_time_naive = self._make_datetime_naive(current_time)
            
            # Принудительное закрытие в конце периода
            if current_time_naive >= end_date_naive and (self.position > 0 or self.position < 0):
                self.close_position(
                    price=current_row['close'],
                    time=current_time_naive,
                    reason="Принудительное закрытие в конце периода"
                )
                continue
            
            # Пропускаем если нет индикаторов
            if pd.isna(current_row['supertrend']) or pd.isna(prev_row['supertrend']):
                continue
            
            # Проверяем условия выхода из позиции
            if self.position > 0:  # Длинная позиция
                # Выход по развороту Supertrend
                if current_row['trend_reversal_to_bearish']:
                    self.close_position(
                        price=current_row['close'],
                        time=current_time_naive,
                        reason="Выход по развороту Supertrend"
                    )
                
                # Выход по стоп-лоссу / тейк-профиту
                elif self.position_avg_price > 0:
                    stop_price = self.position_avg_price * (1 - self.stop_loss_perc/100)
                    take_price = self.position_avg_price * (1 + self.take_profit_perc/100)
                    
                    if current_row['close'] <= stop_price:
                        self.close_position(
                            price=current_row['close'],
                            time=current_time_naive,
                            reason="Стоп-лосс"
                        )
                    elif current_row['close'] >= take_price:
                        self.close_position(
                            price=current_row['close'],
                            time=current_time_naive,
                            reason="Тейк-профит"
                        )
            
            elif self.position < 0:  # Короткая позиция
                # Выход по развороту Supertrend
                if current_row['trend_reversal_to_bullish']:
                    self.close_position(
                        price=current_row['close'],
                        time=current_time_naive,
                        reason="Выход по развороту Supertrend"
                    )
                
                # Выход по стоп-лоссу / тейк-профиту
                elif self.position_avg_price > 0:
                    stop_price = self.position_avg_price * (1 + self.stop_loss_perc/100)
                    take_price = self.position_avg_price * (1 - self.take_profit_perc/100)
                    
                    if current_row['close'] >= stop_price:
                        self.close_position(
                            price=current_row['close'],
                            time=current_time_naive,
                            reason="Стоп-лосс"
                        )
                    elif current_row['close'] <= take_price:
                        self.close_position(
                            price=current_row['close'],
                            time=current_time_naive,
                            reason="Тейк-профит"
                        )
            
            # Проверяем условия входа в позицию
            if self.position == 0:  # Нет открытой позиции
                if current_row['enter_long']:
                    self.enter_position(
                        price=current_row['close'],
                        time=current_time_naive,
                        position_type='long',
                        reason="Вход в лонг по стратегии"
                    )
                elif current_row['enter_short']:
                    self.enter_position(
                        price=current_row['close'],
                        time=current_time_naive,
                        position_type='short',
                        reason="Вход в шорт по стратегии"
                    )
            
            # Записываем текущий капитал в кривую доходности
            self.update_equity_curve(current_row['close'], current_time_naive)
    
    def enter_position(self, price: float, time, position_type: str, reason: str):
        """Вход в позицию"""
        # Рассчитываем количество акций для покупки (100% капитала)
        capital_to_use = self.capital * self.position_size_pct
        
        # Минимальный лот для GAZP - 10 акций
        quantity = capital_to_use / price
        quantity = (quantity // 10) * 10  # Округляем до ближайших 10 акций
        
        if quantity < 10:  # Недостаточно капитала для минимального лота
            logger.warning(f"Недостаточно капитала для входа. Нужно минимум {price * 10:.2f} руб.")
            return
        
        self.position = quantity if position_type == 'long' else -quantity
        self.position_avg_price = price
        self.position_type = position_type
        
        # Записываем сделку
        trade = {
            'time': time,
            'type': 'entry',
            'position_type': position_type,
            'price': price,
            'quantity': self.position,
            'capital_before': self.capital,
            'reason': reason
        }
        self.trades.append(trade)
        
        logger.info(f"{time.strftime('%d.%m.%Y %H:%M') if hasattr(time, 'strftime') else time}: {reason} по цене {price:.2f}, количество: {abs(self.position):.0f}")
    
    def close_position(self, price: float, time, reason: str):
        """Закрытие позиции"""
        if self.position == 0:
            return
        
        # Рассчитываем P&L
        if self.position_type == 'long':
            pnl = (price - self.position_avg_price) * abs(self.position)
        else:  # short
            pnl = (self.position_avg_price - price) * abs(self.position)
        
        self.capital += pnl
        
        # Записываем сделку
        trade = {
            'time': time,
            'type': 'exit',
            'position_type': self.position_type,
            'price': price,
            'quantity': self.position,
            'pnl': pnl,
            'capital_after': self.capital,
            'reason': reason
        }
        self.trades.append(trade)
        
        # Добавляем дневную доходность для расчетов Шарпа/Сортино
        if len(self.equity_curve) > 0:
            prev_equity = self.equity_curve[-1]['equity']
            current_equity = self.capital
            if prev_equity > 0:
                daily_return = (current_equity - prev_equity) / prev_equity
                self.daily_returns.append(daily_return)
        
        logger.info(f"{time.strftime('%d.%m.%Y %H:%M') if hasattr(time, 'strftime') else time}: {reason} по цене {price:.2f}, P&L: {pnl:+.2f} руб.")
        
        # Сбрасываем позицию
        self.position = 0.0
        self.position_avg_price = 0.0
        self.position_type = None
    
    def update_equity_curve(self, current_price: float, time):
        """Обновление кривой доходности"""
        # Рассчитываем текущую стоимость позиции
        position_value = 0.0
        if self.position > 0:  # long
            position_value = (current_price - self.position_avg_price) * self.position
        elif self.position < 0:  # short
            position_value = (self.position_avg_price - current_price) * abs(self.position)
        
        total_equity = self.capital + position_value
        
        # Записываем только если изменился капитал или прошло достаточно времени
        if len(self.equity_curve) == 0 or not hasattr(time, '__sub__') or (hasattr(time, '__sub__') and time - self.equity_curve[-1]['time'] >= timedelta(hours=1)):
            self.equity_curve.append({
                'time': time,
                'equity': total_equity,
                'capital': self.capital,
                'position_value': position_value,
                'price': current_price
            })
    
    def calculate_performance_metrics(self):
        """Расчет метрик производительности"""
        if not self.equity_curve:
            return {}
        
        # Преобразуем кривую доходности в DataFrame
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('time', inplace=True)
        
        # Рассчитываем доходность
        final_equity = equity_df['equity'].iloc[-1]
        total_return_pct = (final_equity - self.initial_capital) / self.initial_capital * 100
        total_pnl = final_equity - self.initial_capital
        
        # Используем сохраненные дневные доходности или рассчитываем из equity_curve
        if not self.daily_returns and len(equity_df) > 1:
            equity_df['return'] = equity_df['equity'].pct_change()
            returns = equity_df['return'].dropna().tolist()
        else:
            returns = self.daily_returns
        
        metrics = {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return_pct': total_return_pct,
            'total_pnl': total_pnl,
        }
        
        if returns:
            returns_series = pd.Series(returns)
            
            # Годовые метрики (предполагаем 252 торговых дня)
            annual_factor = np.sqrt(252)
            
            # Коэффициент Шарпа (безрисковая ставка = 0)
            sharpe_ratio = 0
            if returns_series.std() > 0:
                sharpe_ratio = annual_factor * returns_series.mean() / returns_series.std()
            
            # Коэффициент Сортино (используем только отрицательные доходности)
            negative_returns = returns_series[returns_series < 0]
            sortino_ratio = 0
            if negative_returns.std() > 0:
                sortino_ratio = annual_factor * returns_series.mean() / negative_returns.std()
            
            # Максимальная просадка
            if len(returns) > 0:
                cumulative = (1 + pd.Series(returns)).cumprod()
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max
                max_drawdown_pct = drawdown.min() * 100 if not drawdown.empty else 0
            else:
                max_drawdown_pct = 0
            
            metrics.update({
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'max_drawdown_pct': max_drawdown_pct,
                'avg_daily_return_pct': returns_series.mean() * 100 if len(returns_series) > 0 else 0,
                'daily_volatility_pct': returns_series.std() * 100 if len(returns_series) > 0 else 0,
            })
        
        # Статистика по сделкам
        exit_trades = [t for t in self.trades if t['type'] == 'exit']
        total_trades = len(exit_trades)
        
        if total_trades > 0:
            winning_trades = len([t for t in exit_trades if t.get('pnl', 0) > 0])
            losing_trades = len([t for t in exit_trades if t.get('pnl', 0) < 0])
            
            total_win_pnl = sum(t.get('pnl', 0) for t in exit_trades if t.get('pnl', 0) > 0)
            total_loss_pnl = sum(t.get('pnl', 0) for t in exit_trades if t.get('pnl', 0) < 0)
            
            avg_win = total_win_pnl / winning_trades if winning_trades > 0 else 0
            avg_loss = total_loss_pnl / losing_trades if losing_trades > 0 else 0
            
            metrics.update({
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate_pct': (winning_trades / total_trades) * 100 if total_trades > 0 else 0,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': abs(total_win_pnl / total_loss_pnl) if total_loss_pnl != 0 else float('inf'),
                'largest_win': max((t.get('pnl', 0) for t in exit_trades), default=0),
                'largest_loss': min((t.get('pnl', 0) for t in exit_trades), default=0),
            })
        
        return metrics
    
    def print_results(self, metrics: Dict[str, Any]):
        """Вывод результатов бэктеста"""
        print("\n" + "="*70)
        print("📊 РЕЗУЛЬТАТЫ БЭКТЕСТА СТРАТЕГИИ SUPER TREND + MACD/RSI")
        print("="*70)
        
        print(f"\n📅 Период: 01.01.2024 - 01.01.2025")
        print(f"📈 Инструмент: GAZP (FIGI: {self.figi})")
        print(f"⏰ Таймфрейм: 1 час")
        
        print(f"\n💰 КАПИТАЛ:")
        print(f"  Начальный капитал:     {metrics.get('initial_capital', 0):,.2f} руб.")
        print(f"  Конечный капитал:      {metrics.get('final_equity', 0):,.2f} руб.")
        print(f"  Общая доходность:      {metrics.get('total_return_pct', 0):+.2f}%")
        print(f"  Общий P&L:             {metrics.get('total_pnl', 0):+,.2f} руб.")
        
        print(f"\n📈 МЕТРИКИ РИСКА:")
        print(f"  Коэффициент Шарпа:     {metrics.get('sharpe_ratio', 0):.3f}")
        print(f"  Коэффициент Сортино:   {metrics.get('sortino_ratio', 0):.3f}")
        print(f"  Макс. просадка:        {metrics.get('max_drawdown_pct', 0):.2f}%")
        
        if 'avg_daily_return_pct' in metrics:
            print(f"  Средн. дневная доходн.: {metrics.get('avg_daily_return_pct', 0):.4f}%")
            print(f"  Волатильность:         {metrics.get('daily_volatility_pct', 0):.4f}%")
        
        print(f"\n🎯 СТАТИСТИКА СДЕЛОК:")
        print(f"  Всего сделок:          {metrics.get('total_trades', 0)}")
        print(f"  Прибыльных сделок:     {metrics.get('winning_trades', 0)}")
        print(f"  Убыточных сделок:      {metrics.get('losing_trades', 0)}")
        print(f"  Процент успеха:        {metrics.get('win_rate_pct', 0):.1f}%")
        
        if 'avg_win' in metrics:
            print(f"  Средний выигрыш:       {metrics.get('avg_win', 0):.2f} руб.")
            print(f"  Средний проигрыш:      {metrics.get('avg_loss', 0):.2f} руб.")
            print(f"  Профит-фактор:         {metrics.get('profit_factor', 0):.2f}")
            print(f"  Крупнейший выигрыш:    {metrics.get('largest_win', 0):.2f} руб.")
            print(f"  Крупнейший проигрыш:   {metrics.get('largest_loss', 0):.2f} руб.")
        
        print(f"\n⚙️  ПАРАМЕТРЫ СТРАТЕГИИ:")
        print(f"  ATR период: {self.atr_period}")
        print(f"  Supertrend множитель: {self.supertrend_factor}")
        print(f"  MACD: ({self.macd_fast}, {self.macd_slow}, {self.macd_signal})")
        print(f"  RSI период: {self.rsi_period}")
        print(f"  Стоп-лосс: {self.stop_loss_perc}%")
        print(f"  Тейк-профит: {self.take_profit_perc}%")
        print(f"  В сделку: {self.position_size_pct*100:.0f}% капитала")
        
        print(f"\n" + "="*70)
        
        # Выводим историю сделок
        if self.trades:
            print("\n📋 ИСТОРИЯ СДЕЛОК (только выходы):")
            for i, trade in enumerate(self.trades):
                if trade['type'] == 'exit':
                    pnl_sign = '+' if trade.get('pnl', 0) > 0 else ''
                    time_str = trade['time'].strftime('%d.%m.%Y %H:%M') if hasattr(trade['time'], 'strftime') else str(trade['time'])
                    print(f"  {i+1:3d}. {time_str}: "
                          f"{trade['position_type'].upper()} - "
                          f"Цена: {trade['price']:.2f}, P&L: {pnl_sign}{trade.get('pnl', 0):.2f}, "
                          f"Капитал: {trade.get('capital_after', 0):.2f}, "
                          f"Причина: {trade['reason']}")
        
        print(f"\n" + "="*70)
    
    async def run(self):
        """Запуск полного бэктеста"""
        try:
            # Загружаем данные
            df = await self.fetch_candles()
            if df.empty:
                logger.error("Не удалось загрузить данные для бэктеста")
                return
            
            # Выполняем бэктест
            self.execute_backtest(df)
            
            # Принудительное закрытие если позиция осталась открытой
            if self.position != 0 and len(df) > 0:
                last_price = df['close'].iloc[-1]
                last_time = df.index[-1]
                last_time_naive = self._make_datetime_naive(last_time)
                self.close_position(
                    price=last_price,
                    time=last_time_naive,
                    reason="Принудительное закрытие в конце данных"
                )
            
            # Рассчитываем метрики
            metrics = self.calculate_performance_metrics()
            
            if metrics:
                # Выводим результаты
                self.print_results(metrics)
                
                # Сохраняем результаты в файл
                self.save_results(metrics)
            else:
                logger.error("Не удалось рассчитать метрики производительности")
                
        except Exception as e:
            logger.error(f"Ошибка при выполнении бэктеста: {e}")
            import traceback
            logger.error(f"Подробности: {traceback.format_exc()}")
    
    def save_results(self, metrics: Dict[str, Any]):
        """Сохранение результатов в файл"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'strategy': 'Supertrend + MACD/RSI',
            'period': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'parameters': {
                'atr_period': self.atr_period,
                'supertrend_factor': self.supertrend_factor,
                'macd_fast': self.macd_fast,
                'macd_slow': self.macd_slow,
                'macd_signal': self.macd_signal,
                'rsi_period': self.rsi_period,
                'rsi_overbought': self.rsi_overbought,
                'rsi_oversold': self.rsi_oversold,
                'stop_loss_pct': self.stop_loss_perc,
                'take_profit_pct': self.take_profit_perc,
                'position_size_pct': self.position_size_pct,
            },
            'performance': metrics,
            'trades': [t for t in self.trades if t['type'] == 'exit'],
        }
        
        with open('backtest_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info("✅ Результаты сохранены в backtest_results.json")

async def main():
    """Основная функция"""
    try:
        backtester = SupertrendBacktester()
    except ValueError as e:
        print(f"❌ Ошибка: {e}")
        print("Укажите INVEST_TOKEN в .env файле")
        sys.exit(1)
    
    await backtester.run()

if __name__ == "__main__":
    asyncio.run(main())
