#!/usr/bin/env python3
"""
Загрузчик исторических данных для конкретной пары инструментов
Использует реальные данные через Tinkoff API
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Добавляем корень проекта в путь Python
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

try:
    from tinkoff.invest import Client, CandleInterval
    from tinkoff.invest.utils import now
    print("✅ Tinkoff библиотеки импортированы")
except ImportError as e:
    print(f"❌ Ошибка импорта Tinkoff: {e}")
    sys.exit(1)

class PairDataLoader:
    """Загрузчик данных для пары инструментов"""
    
    def __init__(self):
        self.token = os.getenv('INVEST_TOKEN')
        if not self.token or "ваш_токен" in self.token:
            raise ValueError("❌ Токен Tinkoff API не найден в .env файле")
        print("🚀 PairDataLoader инициализирован")
    
    def find_instrument_by_ticker(self, ticker: str):
        """Находит инструмент по тикеру"""
        try:
            with Client(self.token) as client:
                found_instruments = client.instruments.find_instrument(query=ticker)
                if not found_instruments.instruments:
                    print(f"❌ Инструмент с тикером '{ticker}' не найден")
                    return None
                
                for instrument in found_instruments.instruments:
                    if instrument.ticker == ticker:
                        print(f"✅ Найден инструмент: {instrument.name} ({instrument.ticker}), FIGI: {instrument.figi}")
                        return instrument
                
                print(f"❌ Точное совпадение для тикера '{ticker}' не найдено")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка поиска инструмента '{ticker}': {e}")
            return None
    
    def get_historical_data(self, ticker: str, days: int = 730):
        """
        Получает исторические данные за указанное количество дней
        
        Args:
            ticker: Тикер инструмента
            days: Количество дней истории (по умолчанию 730 = 2 года)
            
        Returns:
            DataFrame с колонками: ['date', 'open', 'high', 'low', 'close', 'volume']
        """
        print(f"📊 Загружаем исторические данные для {ticker} за {days} дней...")
        
        # Находим инструмент
        instrument = self.find_instrument_by_ticker(ticker)
        if not instrument:
            return None
        
        # Рассчитываем даты
        to_date = now()
        from_date = to_date - timedelta(days=days)
        
        try:
            with Client(self.token) as client:
                # Получаем свечи (дневные)
                candles = client.get_all_candles(
                    figi=instrument.figi,
                    from_=from_date,
                    to=to_date,
                    interval=CandleInterval.CANDLE_INTERVAL_DAY
                )
                
                # Конвертируем в список для обработки
                candles_list = list(candles)
                
                if not candles_list:
                    print(f"❌ Нет исторических данных для {ticker}")
                    return None
                
                print(f"✅ Получено {len(candles_list)} свечей для {ticker}")
                
                # Создаем DataFrame
                data = []
                for candle in candles_list:
                    data.append({
                        'date': candle.time,
                        'open': self._quotation_to_float(candle.open),
                        'high': self._quotation_to_float(candle.high),
                        'low': self._quotation_to_float(candle.low),
                        'close': self._quotation_to_float(candle.close),
                        'volume': candle.volume
                    })
                
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df.sort_index(inplace=True)
                
                # Добавляем дополнительные колонки
                df['returns'] = df['close'].pct_change()
                df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
                
                return df
                
        except Exception as e:
            print(f"❌ Ошибка загрузки данных для {ticker}: {e}")
            return None
    
    def _quotation_to_float(self, quotation) -> float:
        """Конвертирует Quotation в float"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def load_pair_data(self, ticker1: str, ticker2: str, days: int = 730):
        """
        Загружает данные для пары инструментов и объединяет их
        """
        print(f"\n{'='*60}")
        print(f"📥 ЗАГРУЗКА ДАННЫХ ДЛЯ ПАРЫ: {ticker1} ↔ {ticker2}")
        print(f"{'='*60}")
        
        # Загружаем данные для первого инструмента
        df1 = self.get_historical_data(ticker1, days)
        if df1 is None:
            print(f"❌ Не удалось загрузить данные для {ticker1}")
            return None, None
        
        # Загружаем данные для второго инструмента
        df2 = self.get_historical_data(ticker2, days)
        if df2 is None:
            print(f"❌ Не удалось загрузить данные для {ticker2}")
            return None, None
        
        # Находим общие даты
        common_dates = df1.index.intersection(df2.index)
        
        if len(common_dates) == 0:
            print("❌ Нет общих дат для пары инструментов")
            return None, None
        
        # Фильтруем данные по общим датам
        df1_aligned = df1.loc[common_dates].copy()
        df2_aligned = df2.loc[common_dates].copy()
        
        print(f"\n📊 РЕЗУЛЬТАТЫ ЗАГРУЗКИ:")
        print(f"   Общих торговых дней: {len(common_dates)}")
        print(f"   Период: {common_dates.min().date()} - {common_dates.max().date()}")
        print(f"   {ticker1}: {df1_aligned['close'].iloc[0]:.2f} → {df1_aligned['close'].iloc[-1]:.2f}")
        print(f"   {ticker2}: {df2_aligned['close'].iloc[0]:.2f} → {df2_aligned['close'].iloc[-1]:.2f}")
        
        # Сохраняем данные в файлы
        self.save_data(df1_aligned, ticker1)
        self.save_data(df2_aligned, ticker2)
        
        return df1_aligned, df2_aligned
    
    def save_data(self, df: pd.DataFrame, ticker: str):
        """Сохраняет данные в CSV файл"""
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        
        filename = data_dir / f"{ticker}_historical.csv"
        df.to_csv(filename)
        print(f"💾 Данные {ticker} сохранены в: {filename}")
    
    def load_from_files(self, ticker1: str, ticker2: str):
        """Загружает данные из сохраненных файлов"""
        data_dir = Path(__file__).parent / "data"
        
        file1 = data_dir / f"{ticker1}_historical.csv"
        file2 = data_dir / f"{ticker2}_historical.csv"
        
        if not file1.exists() or not file2.exists():
            print("❌ Файлы с данными не найдены. Нужно сначала загрузить данные.")
            return None, None
        
        df1 = pd.read_csv(file1, index_col='date', parse_dates=True)
        df2 = pd.read_csv(file2, index_col='date', parse_dates=True)
        
        # Находим общие даты
        common_dates = df1.index.intersection(df2.index)
        df1 = df1.loc[common_dates]
        df2 = df2.loc[common_dates]
        
        print(f"📂 Данные загружены из файлов:")
        print(f"   {ticker1}: {len(df1)} дней")
        print(f"   {ticker2}: {len(df2)} дней")
        print(f"   Период: {df1.index.min().date()} - {df1.index.max().date()}")
        
        return df1, df2

def main():
    """Основная функция для тестирования"""
    import sys
    
    if len(sys.argv) < 3:
        print("""
📊 Загрузчик данных для пары инструментов

Использование:
  python tests/strategies/load_pair_data.py <тикер1> <тикер2> [дни]

Примеры:
  python tests/strategies/load_pair_data.py TGKJ ALRS
  python tests/strategies/load_pair_data.py SBER GAZP 365
        """)
        return
    
    ticker1 = sys.argv[1].upper()
    ticker2 = sys.argv[2].upper()
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 730  # 2 года по умолчанию
    
    print(f"🚀 Загрузка данных для пары: {ticker1} ↔ {ticker2}")
    print(f"   Период: {days} дней (~{days//365} лет)")
    
    try:
        loader = PairDataLoader()
        
        # Пробуем загрузить из файлов
        df1, df2 = loader.load_from_files(ticker1, ticker2)
        
        # Если файлов нет, загружаем через API
        if df1 is None or df2 is None:
            print("\n🔄 Файлы не найдены, загружаем через API...")
            df1, df2 = loader.load_pair_data(ticker1, ticker2, days)
        
        if df1 is not None and df2 is not None:
            print(f"\n✅ Данные успешно загружены!")
            print(f"   Готовы к бэктесту: python tests/strategies/pair_arbitrage_backtest.py")
            return True
        else:
            print("❌ Не удалось загрузить данные")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
