#!/usr/bin/env python3
"""
Скрипт для сканирования сигналов по стратегии Supertrend + MACD/RSI
Таймфрейм: 1 час
Инструмент: GAZP
Использует официальный Tinkoff Invest API
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import pandas as pd
import numpy as np

# Загружаем переменные окружения из .env файла
from dotenv import load_dotenv
load_dotenv()

from tinkoff.invest import AsyncClient, CandleInterval
from tinkoff.invest.utils import now

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('supertrend_scanner.log')
    ]
)
logger = logging.getLogger(__name__)

class SupertrendScanner:
    """Сканер сигналов по стратегии Supertrend + MACD/RSI"""
    
    def __init__(self, token: str = None):
        """
        Инициализация сканера
        
        Args:
            token: Токен Tinkoff Invest API. Если не указан, берется из переменных окружения.
        """
        # Получаем токен: сначала переданный, затем из переменных окружения
        if token is None:
            token = os.getenv('INVEST_TOKEN')
        
        if not token:
            logger.error("❌ Токен не найден. Укажите в .env файле как INVEST_TOKEN")
            raise ValueError("Токен Tinkoff API не найден")
        
        self.token = token
        self.figi = "BBG004730RP0"  # FIGI для GAZP
        
        # Параметры стратегии
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
        
        # Заглушка: предполагаем, что у нас НЕТ актива
        self.has_position = False
        self.position_type = None
        
    async def fetch_hourly_candles(self, days: int = 30) -> pd.DataFrame:
        """Получение часовых свечей за указанный период"""
        logger.info(f"Загрузка часовых свечей для GAZP за последние {days} дней...")
        
        try:
            async with AsyncClient(self.token) as client:
                from_time = now() - timedelta(days=days)
                to_time = now()
                
                candles = []
                async for candle in client.get_all_candles(
                    figi=self.figi,
                    from_=from_time,
                    to=to_time,
                    interval=CandleInterval.CANDLE_INTERVAL_HOUR
                ):
                    candles.append({
                        'time': candle.time,
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
                
                logger.info(f"Получено {len(df)} свечей")
                return df
                
        except Exception as e:
            logger.error(f"Ошибка при получении свечей: {e}")
            import traceback
            logger.error(f"Подробности: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def _quotation_to_float(self, quotation) -> float:
        """Конвертирует Quotation в float"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 5) -> pd.Series:
        """Расчет Average True Range (ATR)"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = true_range.max(axis=1)
        
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def calculate_supertrend(self, df: pd.DataFrame, period: int = 5, factor: float = 3.1) -> pd.DataFrame:
        """Расчет индикатора Supertrend"""
        atr = self.calculate_atr(df, period)
        hl2 = (df['high'] + df['low']) / 2
        
        upper_band = hl2 + (factor * atr)
        lower_band = hl2 - (factor * atr)
        
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
        """Расчет индикатора MACD"""
        ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        
        return pd.DataFrame({
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': macd_line - signal_line
        })
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 13) -> pd.Series:
        """Расчет индикатора RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def analyze_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Анализ сигналов на основе стратегии"""
        if len(df) < 30:
            return {"error": f"Недостаточно данных. Нужно 30 свечей, есть {len(df)}"}
        
        # Расчет индикаторов
        supertrend_df = self.calculate_supertrend(df, self.atr_period, self.supertrend_factor)
        macd_df = self.calculate_macd(df)
        rsi_series = self.calculate_rsi(df, self.rsi_period)
        
        # Добавляем индикаторы в DataFrame
        df = df.copy()
        df['supertrend'] = supertrend_df['supertrend']
        df['supertrend_direction'] = supertrend_df['direction']
        df['macd_line'] = macd_df['macd_line']
        df['macd_signal'] = macd_df['signal_line']
        df['rsi'] = rsi_series
        
        if len(df) < 2:
            return {"error": "Недостаточно свечей для анализа"}
        
        prev_candle = df.iloc[-2]
        current_candle = df.iloc[-1]
        
        # Проверяем бычьи условия ВХОДА
        is_bullish_st = current_candle['supertrend_direction'] == 1
        condition_pullback_long = (
            is_bullish_st and
            (prev_candle['close'] < prev_candle['supertrend']) and
            (current_candle['close'] > current_candle['supertrend'])
        )
        
        macd_bullish = current_candle['macd_line'] > current_candle['macd_signal']
        rsi_not_overbought = current_candle['rsi'] < self.rsi_overbought
        enter_long = condition_pullback_long and macd_bullish and rsi_not_overbought
        
        # Проверяем медвежьи условия ВХОДА
        is_bearish_st = current_candle['supertrend_direction'] == -1
        condition_pullback_short = (
            is_bearish_st and
            (prev_candle['close'] > prev_candle['supertrend']) and
            (current_candle['close'] < current_candle['supertrend'])
        )
        
        macd_bearish = current_candle['macd_line'] < current_candle['macd_signal']
        rsi_not_oversold = current_candle['rsi'] > self.rsi_oversold
        enter_short = condition_pullback_short and macd_bearish and rsi_not_oversold
        
        # Проверяем развороты тренда для ВЫХОДА
        exit_long = is_bearish_st and df.iloc[-2]['supertrend_direction'] != -1
        exit_short = is_bullish_st and df.iloc[-2]['supertrend_direction'] != 1
        
        # Определяем финальный сигнал
        final_signal = "НИЧЕГО"
        signal_type = "НЕТ_СИГНАЛА"
        
        if not self.has_position:
            if enter_long:
                final_signal = "ПОКУПАТЬ"
                signal_type = "ВХОД_ЛОНГ"
            elif enter_short:
                final_signal = "ПРОДАВАТЬ"
                signal_type = "ВХОД_ШОРТ"
        else:
            final_signal = "ДЕРЖАТЬ"
            signal_type = "ЗАГЛУШКА_ДЛЯ_ПОЗИЦИИ"
        
        # Формируем результат
        return {
            "timestamp": datetime.now(),
            "symbol": "GAZP",
            "price": float(current_candle['close']),
            "has_position": self.has_position,
            "position_type": self.position_type,
            "final_signal": final_signal,
            "signal_type": signal_type,
            "indicators": {
                "supertrend": float(current_candle['supertrend']),
                "supertrend_direction": "BULLISH" if is_bullish_st else "BEARISH",
                "macd_line": float(current_candle['macd_line']),
                "macd_signal": float(current_candle['macd_signal']),
                "macd_cross": "BULLISH" if macd_bullish else "BEARISH",
                "rsi": float(current_candle['rsi']),
            },
            "conditions": {
                "pullback_long_condition": bool(condition_pullback_long),
                "pullback_short_condition": bool(condition_pullback_short),
                "macd_bullish": bool(macd_bullish),
                "macd_bearish": bool(macd_bearish),
                "rsi_not_overbought": bool(rsi_not_overbought),
                "rsi_not_oversold": bool(rsi_not_oversold),
            },
            "raw_signals": {
                "enter_long": bool(enter_long),
                "enter_short": bool(enter_short),
                "exit_long": bool(exit_long),
                "exit_short": bool(exit_short),
            },
            "risk_levels": {
                "stop_loss": current_candle['close'] * (1 - self.stop_loss_perc/100),
                "take_profit": current_candle['close'] * (1 + self.take_profit_perc/100),
            }
        }
    
    def print_signal_report(self, result: Dict[str, Any]):
        """Красивый вывод отчета о сигнале"""
        separator = "="*60
        print(f"\n{separator}")
        print(f"СКАНЕР СИГНАЛОВ - {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{separator}")
        
        print(f"\n📊 ИНСТРУМЕНТ: {result['symbol']}")
        print(f"💰 Цена: {result['price']:.2f} руб.")
        print(f"📋 ПОЗИЦИЯ: {'ЕСТЬ' if result['has_position'] else 'НЕТУ'}")
        
        print(f"\n📈 ИНДИКАТОРЫ:")
        print(f"  Supertrend: {result['indicators']['supertrend_direction']} ({result['indicators']['supertrend']:.2f})")
        print(f"  MACD: {result['indicators']['macd_line']:.4f} / {result['indicators']['macd_signal']:.4f}")
        print(f"  RSI: {result['indicators']['rsi']:.2f}")
        
        print(f"\n🎯 УРОВНИ РИСКА:")
        print(f"  Стоп-лосс: {result['risk_levels']['stop_loss']:.2f} ({self.stop_loss_perc}%)")
        print(f"  Тейк-профит: {result['risk_levels']['take_profit']:.2f} ({self.take_profit_perc}%)")
        
        print(f"\n🔍 УСЛОВИЯ СТРАТЕГИИ:")
        for condition, value in result['conditions'].items():
            status = "✅" if value else "❌"
            print(f"  {condition.replace('_', ' ').title()}: {status}")
        
        print(f"\n{separator}")
        print(f"\n🚨 ФИНАЛЬНЫЙ СИГНАЛ: {result['final_signal']}")
        
        if not result['has_position']:
            print(f"📢 РЕКОМЕНДАЦИЯ: {result['final_signal']}")
            if result['final_signal'] == "ПОКУПАТЬ":
                print(f"   ↳ Входить в ЛОНГ по цене ~{result['price']:.2f}")
            elif result['final_signal'] == "ПРОДАВАТЬ":
                print(f"   ↳ Входить в ШОРТ по цене ~{result['price']:.2f}")
        else:
            print(f"📢 СИГНАЛ ДЛЯ ПОЗИЦИИ: {result['final_signal']}")
        
        print(f"\n{separator}\n")
    
    async def scan_once(self):
        """Один запуск сканирования"""
        logger.info("Запуск сканирования...")
        
        df = await self.fetch_hourly_candles(days=30)
        if df.empty:
            logger.error("Не удалось получить данные")
            return
        
        result = self.analyze_signals(df)
        
        if "error" in result:
            logger.error(f"Ошибка анализа: {result['error']}")
            return
        
        self.print_signal_report(result)
        logger.info(f"Финальный сигнал: {result['final_signal']}")

async def main():
    """Основная функция"""
    try:
        scanner = SupertrendScanner()
    except ValueError as e:
        print(f"❌ Ошибка: {e}")
        print("Укажите INVEST_TOKEN в .env файле")
        sys.exit(1)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        await scanner.scan_once()
    else:
        print("Запуск по расписанию...")
        while True:
            await scanner.scan_once()
            await asyncio.sleep(3600)  # Ждем 1 час

if __name__ == "__main__":
    asyncio.run(main())
