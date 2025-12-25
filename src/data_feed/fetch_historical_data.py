#!/usr/bin/env python3
"""
Скрипт для загрузки исторических данных по инструментам (шаг 2 статистического арбитража).
Загружает данные по инструментам из файла, созданного get_instruments_ru.py.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import time
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

# Добавляем корень проекта в путь для импорта модулей
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from tinkoff.invest import Client, CandleInterval, HistoricCandle
from tinkoff.invest.utils import now

# Загружаем переменные окружения
load_dotenv()

class HistoricalDataFetcher:
    """Класс для загрузки исторических данных"""
    
    def __init__(self, max_instruments: int = 50):
        """
        Инициализация загрузчика
        
        Args:
            max_instruments: Максимальное количество инструментов для загрузки
                            (ограничение для тестирования)
        """
        self.token = os.getenv('INVEST_TOKEN')
        if not self.token or "ваш_токен" in self.token:
            print("❌ Токен Tinkoff API не найден в .env файле")
            sys.exit(1)
        
        self.max_instruments = max_instruments
        self.historical_data = {}  # {ticker: DataFrame с историей}
        self.metadata = []  # Метаданные по инструментам
        
        print(f"🚀 Инициализация HistoricalDataFetcher (макс. {max_instruments} инструментов)")
    
    def find_latest_instruments_file(self) -> Optional[Path]:
        """Находит последний CSV файл с инструментами"""
        project_root = Path.cwd()
        instrument_files = list(project_root.glob("instruments_ru_*.csv"))
        
        if not instrument_files:
            print("❌ Не найден файл с инструментами (instruments_ru_*.csv)")
            print("   Сначала запустите: python src/data_feed/get_instruments_ru.py")
            return None
        
        # Сортируем по времени создания (новые сначала)
        instrument_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_file = instrument_files[0]
        
        print(f"📁 Найден файл с инструментами: {latest_file}")
        print(f"   Размер: {latest_file.stat().st_size / 1024:.1f} КБ")
        
        return latest_file
    
    def load_instruments(self, filepath: Path) -> pd.DataFrame:
        """Загружает инструменты из CSV файла"""
        try:
            df = pd.read_csv(filepath)
            print(f"✅ Загружено {len(df)} инструментов из {filepath.name}")
            
            # Ограничиваем количество для тестирования
            if len(df) > self.max_instruments:
                print(f"⚠️  Ограничиваем до {self.max_instruments} инструментов для тестирования")
                df = df.head(self.max_instruments)
            
            return df
            
        except Exception as e:
            print(f"❌ Ошибка загрузки файла {filepath}: {e}")
            sys.exit(1)
    
    def get_historical_data_sync(self, figi: str, days_back: int = 365) -> Optional[pd.DataFrame]:
        """
        Синхронно получает исторические данные по FIGI
        
        Args:
            figi: FIGI инструмента
            days_back: Количество дней истории
        
        Returns:
            DataFrame с колонками: ['date', 'open', 'high', 'low', 'close', 'volume']
        """
        try:
            with Client(self.token) as client:
                # Рассчитываем период
                to_date = now()
                from_date = to_date - timedelta(days=days_back)
                
                # Запрашиваем дневные свечи
                candles = client.get_all_candles(
                    figi=figi,
                    from_=from_date,
                    to=to_date,
                    interval=CandleInterval.CANDLE_INTERVAL_DAY
                )
                
                # Конвертируем в DataFrame
                data = []
                for candle in candles:
                    data.append({
                        'date': candle.time.date(),
                        'open': self._quotation_to_float(candle.open),
                        'high': self._quotation_to_float(candle.high),
                        'low': self._quotation_to_float(candle.low),
                        'close': self._quotation_to_float(candle.close),
                        'volume': candle.volume
                    })
                
                if not data:
                    print(f"   ⚠️  Нет исторических данных для FIGI: {figi}")
                    return None
                
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                return df
                
        except Exception as e:
            print(f"   ❌ Ошибка получения данных для FIGI {figi[:10]}...: {e}")
            return None
    
    def _quotation_to_float(self, quotation) -> float:
        """Конвертация Quotation в float"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def fetch_all_historical_data(self, instruments_df: pd.DataFrame) -> Dict:
        """Загружает исторические данные по всем инструментам"""
        total = len(instruments_df)
        print(f"\n📊 Начинаем загрузку исторических данных для {total} инструментов...")
        print("   (примерно 1-2 секунды на инструмент)")
        print("-" * 60)
        
        successful = 0
        failed = 0
        min_days = 30  # Минимальное количество дней данных для анализа
        
        for i, (_, row) in enumerate(instruments_df.iterrows(), 1):
            ticker = row['ticker']
            figi = row['figi']
            name = row['name']
            
            print(f"[{i:3}/{total}] {ticker:10} - {name[:30]:30}...", end="", flush=True)
            
            # Загружаем исторические данные
            df = self.get_historical_data_sync(figi, days_back=365)
            
            if df is not None and len(df) >= min_days:
                self.historical_data[ticker] = df
                successful += 1
                
                # Сохраняем метаданные
                self.metadata.append({
                    'ticker': ticker,
                    'name': name[:50],
                    'figi': figi,
                    'type': row['type'],
                    'currency': row['currency'],
                    'data_points': len(df),
                    'first_date': df['date'].min().date(),
                    'last_date': df['date'].max().date(),
                    'avg_volume': df['volume'].mean(),
                    'price_change_%': ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100) if len(df) > 1 else 0
                })
                
                print(f" ✅ {len(df)} дней данных")
            else:
                failed += 1
                if df is not None and len(df) < min_days:
                    print(f" ❌ мало данных ({len(df)} < {min_days} дней)")
                else:
                    print(" ❌ ошибка загрузки")
            
            # Пауза между запросами чтобы не превысить лимиты API
            if i < total:
                time.sleep(0.5)
        
        print("-" * 60)
        print(f"📊 Итог: {successful} успешно, {failed} с ошибками")
        
        return self.historical_data
    
    def create_price_matrix(self) -> pd.DataFrame:
        """Создаёт матрицу цен закрытия для всех инструментов"""
        if not self.historical_data:
            print("❌ Нет исторических данных для создания матрицы")
            return pd.DataFrame()
        
        # Собираем все уникальные даты
        all_dates = set()
        for df in self.historical_data.values():
            all_dates.update(df['date'])
        
        # Сортируем даты
        sorted_dates = sorted(all_dates)
        
        # Создаём матрицу
        price_matrix = pd.DataFrame(index=sorted_dates)
        price_matrix.index.name = 'date'
        
        # Заполняем цены закрытия
        for ticker, df in self.historical_data.items():
            # Устанавливаем дату как индекс для быстрого поиска
            df_temp = df.set_index('date')[['close']].copy()
            df_temp.columns = [ticker]
            
            # Объединяем с основной матрицей
            price_matrix = price_matrix.join(df_temp, how='left')
        
        print(f"✅ Создана матрица цен: {price_matrix.shape[0]} дней × {price_matrix.shape[1]} инструментов")
        
        # Удаляем строки с большим количеством пропусков
        threshold = 0.7  # Максимум 70% пропусков в строке
        price_matrix_clean = price_matrix.dropna(thresh=len(price_matrix.columns) * threshold)
        
        if len(price_matrix_clean) < len(price_matrix):
            print(f"⚠️  Удалено {len(price_matrix) - len(price_matrix_clean)} дней с пропусками")
        
        return price_matrix_clean
    
    def calculate_basic_correlations(self, price_matrix: pd.DataFrame) -> pd.DataFrame:
        """Рассчитывает корреляции между инструментами (предварительный анализ)"""
        if price_matrix.empty:
            return pd.DataFrame()
        
        # Рассчитываем матрицу корреляций
        correlation_matrix = price_matrix.corr()
        
        # Находим топ-10 пар с самой высокой корреляцией
        correlations = []
        
        # Преобразуем матрицу корреляций в список пар
        corr_values = correlation_matrix.values
        tickers = correlation_matrix.columns
        
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                corr = corr_values[i, j]
                if not np.isnan(corr):
                    correlations.append({
                        'ticker1': tickers[i],
                        'ticker2': tickers[j],
                        'correlation': corr,
                        'abs_correlation': abs(corr)
                    })
        
        # Сортируем по абсолютной корреляции
        correlations_df = pd.DataFrame(correlations)
        correlations_df = correlations_df.sort_values('abs_correlation', ascending=False)
        
        return correlations_df.head(20)  # Топ-20 пар
    
    def save_results(self, price_matrix: pd.DataFrame, correlations: pd.DataFrame):
        """Сохраняет результаты в CSV файлы"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Сохраняем матрицу цен
        price_file = f"historical_prices_{timestamp}.csv"
        price_matrix.to_csv(price_file)
        print(f"💾 Матрица цен сохранена: {price_file}")
        print(f"   Размер: {price_matrix.shape[0]} строк × {price_matrix.shape[1]} колонок")
        
        # 2. Сохраняем метаданные
        if self.metadata:
            metadata_df = pd.DataFrame(self.metadata)
            metadata_file = f"historical_metadata_{timestamp}.csv"
            metadata_df.to_csv(metadata_file, index=False)
            print(f"💾 Метаданные сохранены: {metadata_file}")
            print(f"   Инструментов: {len(metadata_df)}")
        
        # 3. Сохраняем корреляции
        if not correlations.empty:
            corr_file = f"correlations_{timestamp}.csv"
            correlations.to_csv(corr_file, index=False)
            print(f"💾 Корреляции сохранены: {corr_file}")
            print(f"   Пар: {len(correlations)}")
        
        # 4. Создаем файл со статистикой
        stats = {
            'timestamp': timestamp,
            'total_instruments': len(self.historical_data),
            'trading_days': len(price_matrix),
            'start_date': price_matrix.index.min().strftime('%Y-%m-%d'),
            'end_date': price_matrix.index.max().strftime('%Y-%m-%d'),
            'price_matrix_file': price_file,
            'metadata_file': metadata_file if self.metadata else None,
            'correlations_file': corr_file if not correlations.empty else None
        }
        
        stats_file = f"historical_stats_{timestamp}.txt"
        with open(stats_file, 'w') as f:
            f.write("СТАТИСТИКА ИСТОРИЧЕСКИХ ДАННЫХ\n")
            f.write("=" * 50 + "\n")
            for key, value in stats.items():
                f.write(f"{key:20}: {value}\n")
        
        print(f"📊 Статистика сохранена: {stats_file}")
        
        return {
            'price_file': price_file,
            'metadata_file': metadata_file if self.metadata else None,
            'correlations_file': corr_file if not correlations.empty else None,
            'stats_file': stats_file
        }
    
    def run(self):
        """Основной метод запуска"""
        print("=" * 70)
        print("📈 ЗАГРУЗКА ИСТОРИЧЕСКИХ ДАННЫХ ДЛЯ СТАТИСТИЧЕСКОГО АРБИТРАЖА")
        print("=" * 70)
        
        # 1. Находим файл с инструментами
        instruments_file = self.find_latest_instruments_file()
        if not instruments_file:
            return
        
        # 2. Загружаем инструменты
        instruments_df = self.load_instruments(instruments_file)
        
        # 3. Загружаем исторические данные
        historical_data = self.fetch_all_historical_data(instruments_df)
        
        if not historical_data:
            print("❌ Не удалось загрузить исторические данные")
            return
        
        # 4. Создаем матрицу цен
        price_matrix = self.create_price_matrix()
        
        if price_matrix.empty:
            print("❌ Не удалось создать матрицу цен")
            return
        
        # 5. Рассчитываем предварительные корреляции
        correlations = self.calculate_basic_correlations(price_matrix)
        
        # 6. Сохраняем результаты
        files = self.save_results(price_matrix, correlations)
        
        # 7. Выводим итоговую статистику
        self.print_final_stats(price_matrix, correlations, files)
    
    def print_final_stats(self, price_matrix: pd.DataFrame, correlations: pd.DataFrame, files: dict):
        """Выводит итоговую статистику"""
        print("\n" + "=" * 70)
        print("🎯 ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 70)
        
        print(f"📊 Данные загружены для {len(self.historical_data)} инструментов")
        print(f"📅 Период: {price_matrix.index.min().date()} - {price_matrix.index.max().date()}")
        print(f"📈 Торговых дней: {len(price_matrix)}")
        
        # Статистика по инструментам
        if self.metadata:
            metadata_df = pd.DataFrame(self.metadata)
            print(f"\n📋 Распределение по типам:")
            print(metadata_df['type'].value_counts().to_string())
            
            print(f"\n💰 Среднее изменение цены за период:")
            print(f"   Макс рост: {metadata_df['price_change_%'].max():.1f}%")
            print(f"   Мин рост: {metadata_df['price_change_%'].min():.1f}%")
            print(f"   Среднее: {metadata_df['price_change_%'].mean():.1f}%")
        
        # Топ коррелирующих пар
        if not correlations.empty:
            print(f"\n🔗 ТОП-5 коррелирующих пар:")
            for i, (_, row) in enumerate(correlations.head(5).iterrows(), 1):
                print(f"   {i}. {row['ticker1']} ↔ {row['ticker2']}: {row['correlation']:.3f}")
        
        print(f"\n💾 Файлы результатов:")
        for key, value in files.items():
            if value:
                print(f"   {key:20}: {value}")
        
        print("\n🎯 Следующий шаг: Анализ пар для статистического арбитража")
        print("=" * 70)

def main():
    """Точка входа"""
    try:
        # Можно изменить max_instruments для тестирования
        fetcher = HistoricalDataFetcher(max_instruments=30)  # Начнем с 30 инструментов
        fetcher.run()
        
    except KeyboardInterrupt:
        print("\n⏹️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
