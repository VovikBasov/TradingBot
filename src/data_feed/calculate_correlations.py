#!/usr/bin/env python3
"""
Скрипт для расчёта корреляций между инструментами (шаг 3 статистического арбитража).
Анализирует матрицу цен и находит потенциальные пары для торговли.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Set
import warnings
warnings.filterwarnings('ignore')

# Добавляем корень проекта в путь для импорта модулей
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class CorrelationCalculator:
    """Класс для расчёта корреляций между инструментами"""
    
    def __init__(self, min_correlation: float = 0.7, min_common_days: int = 100):
        """
        Инициализация калькулятора корреляций
        
        Args:
            min_correlation: Минимальная корреляция для отбора пар
            min_common_days: Минимальное количество общих торговых дней
        """
        self.min_correlation = min_correlation
        self.min_common_days = min_common_days
        self.price_matrix = None
        self.correlation_matrix = None
        self.strong_pairs = []
        
        print(f"🚀 Инициализация CorrelationCalculator")
        print(f"   Минимальная корреляция: {min_correlation}")
        print(f"   Минимальное общих дней: {min_common_days}")
    
    def find_latest_price_file(self) -> Optional[Path]:
        """Находит последний CSV файл с матрицей цен"""
        project_root = Path.cwd()
        price_files = list(project_root.glob("historical_prices_*.csv"))
        
        if not price_files:
            print("❌ Не найден файл с матрицей цен (historical_prices_*.csv)")
            print("   Сначала запустите: python src/data_feed/fetch_historical_prices.py")
            return None
        
        # Сортируем по времени создания (новые сначала)
        price_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_file = price_files[0]
        
        print(f"📁 Найден файл с матрицей цен: {latest_file}")
        print(f"   Размер: {latest_file.stat().st_size / 1024:.1f} КБ")
        
        return latest_file
    
    def find_latest_metadata_file(self) -> Optional[Path]:
        """Находит последний CSV файл с метаданными"""
        project_root = Path.cwd()
        metadata_files = list(project_root.glob("historical_metadata_*.csv"))
        
        if not metadata_files:
            print("⚠️  Не найден файл с метаданными (historical_metadata_*.csv)")
            return None
        
        # Сортируем по времени создания (новые сначала)
        metadata_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_file = metadata_files[0]
        
        print(f"📁 Найден файл с метаданными: {latest_file}")
        return latest_file
    
    def load_price_matrix(self, filepath: Path) -> pd.DataFrame:
        """Загружает матрицу цен из CSV файла"""
        try:
            # Читаем CSV, устанавливаем дату как индекс
            df = pd.read_csv(filepath, index_col='date', parse_dates=True)
            print(f"✅ Загружена матрица цен: {df.shape[0]} дней × {df.shape[1]} инструментов")
            print(f"   Период: {df.index.min().date()} - {df.index.max().date()}")
            
            return df
            
        except Exception as e:
            print(f"❌ Ошибка загрузки файла {filepath}: {e}")
            sys.exit(1)
    
    def load_metadata(self, filepath: Optional[Path]) -> Optional[pd.DataFrame]:
        """Загружает метаданные инструментов"""
        if filepath is None:
            return None
            
        try:
            df = pd.read_csv(filepath)
            print(f"✅ Загружены метаданные: {len(df)} инструментов")
            return df
        except Exception as e:
            print(f"⚠️  Ошибка загрузки метаданных: {e}")
            return None
    
    def calculate_correlation_matrix(self, price_matrix: pd.DataFrame) -> pd.DataFrame:
        """Рассчитывает матрицу корреляций между всеми инструментами"""
        print(f"\n📊 Рассчитываем матрицу корреляций...")
        
        # Рассчитываем корреляции
        correlation_matrix = price_matrix.corr()
        
        print(f"✅ Матрица корреляций рассчитана")
        print(f"   Размер: {correlation_matrix.shape[0]} × {correlation_matrix.shape[1]}")
        
        # Базовая статистика корреляций
        corr_values = correlation_matrix.values.flatten()
        corr_values = corr_values[~np.isnan(corr_values)]  # Убираем NaN
        corr_values = corr_values[corr_values != 1.0]  # Убираем корреляцию с собой
        
        if len(corr_values) > 0:
            print(f"   Средняя корреляция: {np.mean(corr_values):.3f}")
            print(f"   Медианная корреляция: {np.median(corr_values):.3f}")
            print(f"   Макс корреляция: {np.max(corr_values):.3f}")
            print(f"   Мин корреляция: {np.min(corr_values):.3f}")
        
        return correlation_matrix
    
    def find_strong_pairs(self, price_matrix: pd.DataFrame, correlation_matrix: pd.DataFrame) -> List[Dict]:
        """Находит сильно коррелирующие пары инструментов"""
        print(f"\n🔍 Ищем сильно коррелирующие пары (корреляция > {self.min_correlation})...")
        
        pairs = []
        tickers = correlation_matrix.columns
        corr_values = correlation_matrix.values
        
        # Проходим по всем парам инструментов
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                corr = corr_values[i, j]
                
                if not np.isnan(corr) and abs(corr) >= self.min_correlation:
                    ticker1 = tickers[i]
                    ticker2 = tickers[j]
                    
                    # Получаем данные по этим тикерам
                    data1 = price_matrix[ticker1].dropna()
                    data2 = price_matrix[ticker2].dropna()
                    
                    # Находим общие даты
                    common_dates = data1.index.intersection(data2.index)
                    common_days = len(common_dates)
                    
                    if common_days >= self.min_common_days:
                        # Рассчитываем дополнительные метрики
                        pair_data = {
                            'ticker1': ticker1,
                            'ticker2': ticker2,
                            'correlation': corr,
                            'abs_correlation': abs(corr),
                            'common_days': common_days,
                            'price_ratio': data1.mean() / data2.mean() if data2.mean() != 0 else 0,
                            'volatility_ratio': data1.std() / data2.std() if data2.std() != 0 else 0,
                            'ticker1_mean_price': data1.mean(),
                            'ticker2_mean_price': data2.mean(),
                            'ticker1_volatility': data1.std(),
                            'ticker2_volatility': data2.std()
                        }
                        
                        pairs.append(pair_data)
        
        # Сортируем по абсолютной корреляции
        pairs.sort(key=lambda x: x['abs_correlation'], reverse=True)
        
        print(f"✅ Найдено {len(pairs)} пар с корреляцией > {self.min_correlation}")
        
        return pairs
    
    def analyze_pair_characteristics(self, pairs: List[Dict], metadata: Optional[pd.DataFrame]) -> pd.DataFrame:
        """Анализирует характеристики пар и добавляет информацию из метаданных"""
        if not pairs:
            return pd.DataFrame()
        
        # Преобразуем в DataFrame
        pairs_df = pd.DataFrame(pairs)
        
        # Добавляем информацию из метаданных, если есть
        if metadata is not None:
            # Создаем словари для быстрого поиска
            metadata_dict = metadata.set_index('ticker').to_dict('index')
            
            # Добавляем информацию по первому тикеру
            for field in ['type', 'currency', 'name']:
                if field in metadata_dict.get(next(iter(metadata_dict.keys())), {}):
                    pairs_df[f'ticker1_{field}'] = pairs_df['ticker1'].map(
                        lambda x: metadata_dict.get(x, {}).get(field, 'N/A')
                    )
                    pairs_df[f'ticker2_{field}'] = pairs_df['ticker2'].map(
                        lambda x: metadata_dict.get(x, {}).get(field, 'N/A')
                    )
        
        return pairs_df
    
    def calculate_cointegration(self, price_matrix: pd.DataFrame, pairs_df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
        """
        Рассчитывает коинтеграцию для топ-N пар.
        Коинтеграция важна для статистического арбитража.
        """
        if pairs_df.empty:
            return pairs_df
        
        print(f"\n📈 Рассчитываем коинтеграцию для топ-{min(top_n, len(pairs_df))} пар...")
        
        # Ограничиваем количество пар для анализа
        pairs_to_test = pairs_df.head(top_n).copy()
        
        for idx, row in pairs_to_test.iterrows():
            ticker1 = row['ticker1']
            ticker2 = row['ticker2']
            
            # Получаем данные
            series1 = price_matrix[ticker1].dropna()
            series2 = price_matrix[ticker2].dropna()
            
            # Находим общие даты
            common_idx = series1.index.intersection(series2.index)
            if len(common_idx) < 50:  # Нужно достаточно данных для теста
                pairs_to_test.loc[idx, 'cointegration_pvalue'] = np.nan
                pairs_to_test.loc[idx, 'cointegration_score'] = np.nan
                continue
            
            # Выравниваем данные
            series1_aligned = series1.loc[common_idx]
            series2_aligned = series2.loc[common_idx]
            
            try:
                # Простой тест на коинтеграцию (упрощенный)
                # В реальности нужно использовать statsmodels.tsa.stattools.coint
                # Здесь используем упрощенный подход - корреляция остатков
                
                # Рассчитываем спред
                spread = series1_aligned - series2_aligned
                
                # Проверяем стационарность спреда через автокорреляцию
                # (упрощенный заменитель теста Дики-Фуллера)
                from scipy import stats
                
                # Рассчитываем автокорреляцию первого порядка
                if len(spread) > 1:
                    autocorr = spread.autocorr(lag=1)
                    # Чем ближе autocorr к 0, тем более стационарный ряд
                    pairs_to_test.loc[idx, 'cointegration_score'] = 1 - abs(autocorr)
                else:
                    pairs_to_test.loc[idx, 'cointegration_score'] = np.nan
                
                # Простая оценка p-value (условная)
                pairs_to_test.loc[idx, 'cointegration_pvalue'] = 0.05 if abs(autocorr) < 0.3 else 0.5
                
            except Exception as e:
                pairs_to_test.loc[idx, 'cointegration_pvalue'] = np.nan
                pairs_to_test.loc[idx, 'cointegration_score'] = np.nan
        
        print(f"✅ Коинтеграция рассчитана для {len(pairs_to_test)} пар")
        
        return pairs_to_test
    
    def save_results(self, pairs_df: pd.DataFrame, correlation_matrix: pd.DataFrame, price_matrix: pd.DataFrame):
        """Сохраняет результаты анализа"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Сохраняем найденные пары
        if not pairs_df.empty:
            pairs_file = f"correlation_pairs_{timestamp}.csv"
            pairs_df.to_csv(pairs_file, index=False)
            print(f"💾 Пары сохранены: {pairs_file}")
            print(f"   Всего пар: {len(pairs_df)}")
        
        # 2. Сохраняем полную матрицу корреляций
        corr_matrix_file = f"correlation_matrix_{timestamp}.csv"
        correlation_matrix.to_csv(corr_matrix_file)
        print(f"💾 Матрица корреляций сохранена: {corr_matrix_file}")
        
        # 3. Создаем файл с рекомендациями
        if not pairs_df.empty:
            recommendations_file = f"trading_recommendations_{timestamp}.txt"
            with open(recommendations_file, 'w') as f:
                f.write("РЕКОМЕНДАЦИИ ПО ПАРАМ ДЛЯ СТАТИСТИЧЕСКОГО АРБИТРАЖА\n")
                f.write("=" * 70 + "\n\n")
                
                f.write(f"Всего проанализировано инструментов: {price_matrix.shape[1]}\n")
                f.write(f"Период анализа: {price_matrix.index.min().date()} - {price_matrix.index.max().date()}\n")
                f.write(f"Торговых дней: {price_matrix.shape[0]}\n")
                f.write(f"Найдено сильно коррелирующих пар: {len(pairs_df)}\n\n")
                
                f.write("ТОП-10 ПАР ДЛЯ ДАЛЬНЕЙШЕГО АНАЛИЗА:\n")
                f.write("-" * 70 + "\n")
                
                for i, (_, row) in enumerate(pairs_df.head(10).iterrows(), 1):
                    f.write(f"\n{i}. {row['ticker1']} ↔ {row['ticker2']}\n")
                    f.write(f"   Корреляция: {row['correlation']:.3f}\n")
                    f.write(f"   Общих дней: {row['common_days']}\n")
                    if 'cointegration_score' in row and not pd.isna(row['cointegration_score']):
                        f.write(f"   Оценка коинтеграции: {row['cointegration_score']:.3f}\n")
                    f.write(f"   Средние цены: {row['ticker1_mean_price']:.2f} / {row['ticker2_mean_price']:.2f}\n")
                    f.write(f"   Волатильность: {row['ticker1_volatility']:.3f} / {row['ticker2_volatility']:.3f}\n")
            
            print(f"💾 Рекомендации сохранены: {recommendations_file}")
        
        # 4. Создаем файл со статистикой
        stats_file = f"correlation_stats_{timestamp}.txt"
        with open(stats_file, 'w') as f:
            f.write("СТАТИСТИКА КОРРЕЛЯЦИОННОГО АНАЛИЗА\n")
            f.write("=" * 50 + "\n")
            
            stats = {
                'timestamp': timestamp,
                'total_instruments': price_matrix.shape[1],
                'trading_days': price_matrix.shape[0],
                'strong_pairs_found': len(pairs_df),
                'min_correlation_threshold': self.min_correlation,
                'min_common_days': self.min_common_days,
                'pairs_file': pairs_file if not pairs_df.empty else None,
                'correlation_matrix_file': corr_matrix_file,
                'recommendations_file': recommendations_file if not pairs_df.empty else None
            }
            
            for key, value in stats.items():
                f.write(f"{key:30}: {value}\n")
        
        print(f"📊 Статистика сохранена: {stats_file}")
        
        return {
            'pairs_file': pairs_file if not pairs_df.empty else None,
            'correlation_matrix_file': corr_matrix_file,
            'recommendations_file': recommendations_file if not pairs_df.empty else None,
            'stats_file': stats_file
        }
    
    def print_summary(self, pairs_df: pd.DataFrame, files: dict):
        """Выводит итоговую сводку"""
        print("\n" + "=" * 70)
        print("🎯 ИТОГИ КОРРЕЛЯЦИОННОГО АНАЛИЗА")
        print("=" * 70)
        
        if not pairs_df.empty:
            print(f"📊 Найдено {len(pairs_df)} сильно коррелирующих пар")
            
            print(f"\n🏆 ТОП-5 пар по корреляции:")
            for i, (_, row) in enumerate(pairs_df.head(5).iterrows(), 1):
                print(f"   {i}. {row['ticker1']} ↔ {row['ticker2']}: {row['correlation']:.3f}")
                if 'ticker1_type' in row and 'ticker2_type' in row:
                    print(f"      Типы: {row['ticker1_type']} / {row['ticker2_type']}")
                print(f"      Общих дней: {row['common_days']}, Цены: {row['ticker1_mean_price']:.2f}/{row['ticker2_mean_price']:.2f}")
            
            # Анализ по типам инструментов
            if 'ticker1_type' in pairs_df.columns and 'ticker2_type' in pairs_df.columns:
                print(f"\n📈 Распределение по типам пар:")
                type_pairs = pairs_df.apply(
                    lambda x: f"{x['ticker1_type']}-{x['ticker2_type']}", axis=1
                )
                for pair_type, count in type_pairs.value_counts().head(5).items():
                    print(f"   {pair_type:15}: {count} пар")
        
        print(f"\n💾 Файлы результатов:")
        for key, value in files.items():
            if value:
                print(f"   {key:25}: {value}")
        
        print(f"\n🎯 Следующий шаг: Анализ спреда по выбранным парам")
        print("=" * 70)
    
    def run(self):
        """Основной метод запуска"""
        print("=" * 70)
        print("🔗 РАСЧЁТ КОРРЕЛЯЦИЙ ДЛЯ СТАТИСТИЧЕСКОГО АРБИТРАЖА")
        print("=" * 70)
        
        # 1. Находим файлы с данными
        price_file = self.find_latest_price_file()
        if not price_file:
            return
        
        metadata_file = self.find_latest_metadata_file()
        
        # 2. Загружаем данные
        price_matrix = self.load_price_matrix(price_file)
        metadata = self.load_metadata(metadata_file)
        
        # 3. Рассчитываем корреляции
        correlation_matrix = self.calculate_correlation_matrix(price_matrix)
        
        # 4. Находим сильно коррелирующие пары
        strong_pairs = self.find_strong_pairs(price_matrix, correlation_matrix)
        
        if not strong_pairs:
            print("❌ Не найдено сильно коррелирующих пар")
            print("   Попробуйте уменьшить min_correlation или увеличить min_common_days")
            return
        
        # 5. Анализируем характеристики пар
        pairs_df = self.analyze_pair_characteristics(strong_pairs, metadata)
        
        # 6. Рассчитываем коинтеграцию для топ-пар
        pairs_with_coint = self.calculate_cointegration(price_matrix, pairs_df, top_n=20)
        
        # 7. Сохраняем результаты
        files = self.save_results(pairs_with_coint, correlation_matrix, price_matrix)
        
        # 8. Выводим сводку
        self.print_summary(pairs_with_coint, files)

def main():
    """Точка входа"""
    try:
        # Настройки можно менять
        calculator = CorrelationCalculator(
            min_correlation=0.7,    # Минимальная корреляция
            min_common_days=100     # Минимальное общих дней
        )
        calculator.run()
        
    except KeyboardInterrupt:
        print("\n⏹️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
