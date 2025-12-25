#!/usr/bin/env python3
"""
ПРОДВИНУТЫЙ скрипт для поиска коинтегрированных пар для статистического арбитража.
Использует настоящие статистические тесты: корреляция + коинтеграция + ADF тест.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# Добавляем корень проекта в путь для импорта модулей
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Импорты для статистических тестов
try:
    from statsmodels.tsa.stattools import coint, adfuller
    from scipy import stats
    STATSMODELS_AVAILABLE = True
except ImportError:
    print("❌ Требуются дополнительные библиотеки. Установите:")
    print("   pip install statsmodels scipy")
    STATSMODELS_AVAILABLE = False
    sys.exit(1)

class CointegratedPairsFinder:
    """Класс для поиска коинтегрированных пар с полным статистическим анализом"""
    
    def __init__(self, 
                 min_correlation: float = 0.7,
                 coint_pvalue_threshold: float = 0.05,
                 adf_pvalue_threshold: float = 0.05,
                 min_common_days: int = 100):
        """
        Инициализация анализатора
        
        Args:
            min_correlation: Минимальная корреляция для предварительного фильтра
            coint_pvalue_threshold: Максимальный p-value для теста коинтеграции
            adf_pvalue_threshold: Максимальный p-value для ADF теста спреда
            min_common_days: Минимальное количество общих торговых дней
        """
        if not STATSMODELS_AVAILABLE:
            print("❌ Библиотеки statsmodels/scipy не установлены")
            sys.exit(1)
        
        self.min_correlation = min_correlation
        self.coint_pvalue_threshold = coint_pvalue_threshold
        self.adf_pvalue_threshold = adf_pvalue_threshold
        self.min_common_days = min_common_days
        
        self.price_matrix = None
        self.metadata = None
        self.cointegrated_pairs = []
        
        print("🚀 Инициализация CointegratedPairsFinder")
        print("   Используемые статистические тесты:")
        print("   - Тест коинтеграции Engle-Granger (coint)")
        print("   - ADF тест на стационарность (adfuller)")
        print("   - Линейная регрессия для hedge ratio")
        print(f"\n   Параметры:")
        print(f"   - Минимальная корреляция: {min_correlation}")
        print(f"   - Max p-value коинтеграции: {coint_pvalue_threshold}")
        print(f"   - Max p-value ADF теста: {adf_pvalue_threshold}")
        print(f"   - Минимальное общих дней: {min_common_days}")
    
    def find_latest_price_file(self) -> Optional[Path]:
        """Находит последний CSV файл с матрицей цен"""
        project_root = Path.cwd()
        price_files = list(project_root.glob("historical_prices_*.csv"))
        
        if not price_files:
            print("❌ Не найден файл с матрицей цен (historical_prices_*.csv)")
            print("   Сначала запустите: python src/data_feed/fetch_historical_prices.py")
            return None
        
        price_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return price_files[0]
    
    def find_latest_metadata_file(self) -> Optional[Path]:
        """Находит последний CSV файл с метаданными"""
        project_root = Path.cwd()
        metadata_files = list(project_root.glob("historical_metadata_*.csv"))
        
        if not metadata_files:
            print("⚠️  Не найден файл с метаданными (historical_metadata_*.csv)")
            return None
        
        metadata_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return metadata_files[0]
    
    def load_data(self) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
        """Загружает все необходимые данные"""
        print("\n📁 Загрузка данных...")
        
        # Загружаем матрицу цен
        price_file = self.find_latest_price_file()
        if not price_file:
            return None, None
        
        self.price_matrix = pd.read_csv(price_file, index_col='date', parse_dates=True)
        print(f"✅ Матрица цен: {self.price_matrix.shape[0]} дней × {self.price_matrix.shape[1]} инструментов")
        print(f"   Период: {self.price_matrix.index.min().date()} - {self.price_matrix.index.max().date()}")
        
        # Загружаем метаданные
        metadata_file = self.find_latest_metadata_file()
        if metadata_file:
            self.metadata = pd.read_csv(metadata_file)
            print(f"✅ Метаданные: {len(self.metadata)} инструментов")
        
        return self.price_matrix, self.metadata
    
    def calculate_hedge_ratio(self, series1: pd.Series, series2: pd.Series) -> Tuple[float, float, float]:
        """
        Рассчитывает hedge ratio (коэффициент хеджирования) через линейную регрессию
        Возвращает: (hedge_ratio, r_squared, intercept)
        """
        # Выравниваем данные по общим датам
        common_idx = series1.index.intersection(series2.index)
        if len(common_idx) < self.min_common_days:
            return np.nan, np.nan, np.nan
        
        x = series2.loc[common_idx].values
        y = series1.loc[common_idx].values
        
        # Линейная регрессия: y = hedge_ratio * x + intercept
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        
        return slope, r_squared, intercept
    
    def test_cointegration(self, series1: pd.Series, series2: pd.Series) -> Tuple[float, float, bool]:
        """
        Тест коинтеграции Engle-Granger
        Возвращает: (test_statistic, p_value, is_cointegrated)
        """
        # Выравниваем данные
        common_idx = series1.index.intersection(series2.index)
        if len(common_idx) < self.min_common_days:
            return np.nan, np.nan, False
        
        s1 = series1.loc[common_idx].values
        s2 = series2.loc[common_idx].values
        
        # Тест коинтеграции
        test_stat, p_value, _ = coint(s1, s2)
        is_cointegrated = p_value < self.coint_pvalue_threshold
        
        return test_stat, p_value, is_cointegrated
    
    def test_spread_stationarity(self, spread: pd.Series) -> Tuple[float, float, bool]:
        """
        ADF тест на стационарность спреда
        Возвращает: (adf_statistic, p_value, is_stationary)
        """
        if len(spread) < 50:  # ADF тест требует достаточное количество данных
            return np.nan, np.nan, False
        
        # ADF тест (Augmented Dickey-Fuller)
        adf_stat, p_value, _, _, _, _ = adfuller(spread.dropna(), autolag='AIC')
        is_stationary = p_value < self.adf_pvalue_threshold
        
        return adf_stat, p_value, is_stationary
    
    def calculate_spread_metrics(self, spread: pd.Series) -> Dict:
        """Рассчитывает метрики спреда для торговли"""
        if len(spread) < 10:
            return {}
        
        spread_series = spread.dropna()
        
        metrics = {
            'spread_mean': spread_series.mean(),
            'spread_std': spread_series.std(),
            'spread_min': spread_series.min(),
            'spread_max': spread_series.max(),
            'half_life': self.calculate_half_life(spread_series),
            'hurst_exponent': self.calculate_hurst_exponent(spread_series),
            'z_score_current': 0,  # Будет рассчитано позже при мониторинге
            'entry_threshold_std': 2.0,  # Рекомендуемый порог входа
            'exit_threshold_std': 0.5   # Рекомендуемый порог выхода
        }
        
        return metrics
    
    def calculate_half_life(self, spread: pd.Series) -> float:
        """Рассчитывает период полураспада (half-life) для спреда"""
        try:
            spread_lag = spread.shift(1)
            spread_ret = spread - spread_lag
            spread_lag = spread_lag.iloc[1:]
            spread_ret = spread_ret.iloc[1:]
            
            # Оцениваем коэффициент автокорреляции
            model = stats.linregress(spread_lag.values, spread_ret.values)
            beta = model.slope
            
            if beta >= 0:
                return np.inf  # Нестационарный процесс
                
            half_life = -np.log(2) / beta
            return half_life
            
        except:
            return np.nan
    
    def calculate_hurst_exponent(self, spread: pd.Series, max_lag: int = 20) -> float:
        """Рассчитывает экспоненту Херста (мера персистентности)"""
        try:
            lags = range(2, min(max_lag, len(spread)//2))
            tau = []
            
            for lag in lags:
                # Вычисляем стандартное отклонение разностей
                spread_diff = spread.diff(lag).dropna()
                if len(spread_diff) > 0:
                    tau.append(np.std(spread_diff))
                else:
                    tau.append(np.nan)
            
            # Убираем NaN значения
            valid_lags = []
            valid_tau = []
            for lag, t in zip(lags, tau):
                if not np.isnan(t):
                    valid_lags.append(lag)
                    valid_tau.append(t)
            
            if len(valid_lags) < 3:
                return np.nan
            
            # Линейная регрессия в логарифмическом масштабе
            x = np.log(valid_lags)
            y = np.log(valid_tau)
            
            slope, _, _, _, _ = stats.linregress(x, y)
            hurst = slope / 2.0
            
            return hurst
            
        except:
            return np.nan
    
    def find_all_pairs(self) -> List[Dict]:
        """Находит все потенциальные пары и проводит полный анализ"""
        if self.price_matrix is None:
            print("❌ Матрица цен не загружена")
            return []
        
        print(f"\n🔍 Поиск коинтегрированных пар среди {self.price_matrix.shape[1]} инструментов...")
        print("   Этап 1/3: Предварительный фильтр по корреляции")
        
        tickers = self.price_matrix.columns.tolist()
        n_tickers = len(tickers)
        pairs = []
        
        # Этап 1: Быстрый фильтр по корреляции
        for i in range(n_tickers):
            for j in range(i + 1, n_tickers):
                ticker1 = tickers[i]
                ticker2 = tickers[j]
                
                # Получаем данные
                data1 = self.price_matrix[ticker1].dropna()
                data2 = self.price_matrix[ticker2].dropna()
                
                # Находим общие даты
                common_idx = data1.index.intersection(data2.index)
                if len(common_idx) < self.min_common_days:
                    continue
                
                # Рассчитываем корреляцию
                corr = data1.loc[common_idx].corr(data2.loc[common_idx])
                
                if abs(corr) >= self.min_correlation:
                    pairs.append({
                        'ticker1': ticker1,
                        'ticker2': ticker2,
                        'correlation': corr,
                        'common_days': len(common_idx)
                    })
        
        print(f"   Найдено {len(pairs)} пар с корреляцией > {self.min_correlation}")
        print(f"   Этап 2/3: Тест коинтеграции Engle-Granger")
        
        # Этап 2: Тест коинтеграции
        cointegrated_pairs = []
        for i, pair in enumerate(pairs):
            ticker1 = pair['ticker1']
            ticker2 = pair['ticker2']
            
            print(f"   Пара {i+1}/{len(pairs)}: {ticker1} ↔ {ticker2}", end="", flush=True)
            
            series1 = self.price_matrix[ticker1].dropna()
            series2 = self.price_matrix[ticker2].dropna()
            
            # Тест коинтеграции
            coint_stat, coint_pvalue, is_cointegrated = self.test_cointegration(series1, series2)
            
            if is_cointegrated:
                print(f" ✅ коинтегрирована (p={coint_pvalue:.4f})")
                
                # Рассчитываем hedge ratio
                hedge_ratio, r_squared, intercept = self.calculate_hedge_ratio(series1, series2)
                
                if not np.isnan(hedge_ratio):
                    # Строим спред
                    common_idx = series1.index.intersection(series2.index)
                    spread = series1.loc[common_idx] - hedge_ratio * series2.loc[common_idx]
                    
                    # ADF тест спреда
                    adf_stat, adf_pvalue, is_stationary = self.test_spread_stationarity(spread)
                    
                    if is_stationary:
                        # Рассчитываем метрики спреда
                        spread_metrics = self.calculate_spread_metrics(spread)
                        
                        # Собираем полную информацию
                        pair_data = {
                            **pair,
                            'coint_statistic': coint_stat,
                            'coint_pvalue': coint_pvalue,
                            'adf_statistic': adf_stat,
                            'adf_pvalue': adf_pvalue,
                            'hedge_ratio': hedge_ratio,
                            'regression_intercept': intercept,
                            'regression_r_squared': r_squared,
                            'is_cointegrated': is_cointegrated,
                            'is_spread_stationary': is_stationary,
                            **spread_metrics
                        }
                        
                        # Добавляем информацию из метаданных
                        if self.metadata is not None:
                            metadata_dict = self.metadata.set_index('ticker').to_dict('index')
                            
                            for field in ['type', 'currency', 'name']:
                                if field in metadata_dict.get(ticker1, {}):
                                    pair_data[f'ticker1_{field}'] = metadata_dict[ticker1].get(field, 'N/A')
                                    pair_data[f'ticker2_{field}'] = metadata_dict[ticker2].get(field, 'N/A')
                        
                        cointegrated_pairs.append(pair_data)
            else:
                print(f" ❌ не коинтегрирована (p={coint_pvalue:.4f})" if not np.isnan(coint_pvalue) else " ❌ недостаточно данных")
        
        print(f"   Этап 3/3: ADF тест спреда")
        print(f"   ✅ Найдено {len(cointegrated_pairs)} коинтегрированных пар со стационарным спредом")
        
        return cointegrated_pairs
    
    def save_results(self, pairs: List[Dict]):
        """Сохраняет результаты анализа"""
        if not pairs:
            print("❌ Нет данных для сохранения")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Сохраняем полную информацию о парах
        pairs_df = pd.DataFrame(pairs)
        
        # Сортируем по качеству (комбинированная метрика)
        if 'coint_pvalue' in pairs_df.columns and 'adf_pvalue' in pairs_df.columns:
            # Чем меньше p-value, тем лучше
            pairs_df['quality_score'] = 1 / (pairs_df['coint_pvalue'] * pairs_df['adf_pvalue'])
            pairs_df = pairs_df.sort_values('quality_score', ascending=False)
        
        pairs_file = f"cointegrated_pairs_{timestamp}.csv"
        pairs_df.to_csv(pairs_file, index=False)
        print(f"\n💾 Коинтегрированные пары сохранены: {pairs_file}")
        print(f"   Всего пар: {len(pairs_df)}")
        
        # 2. Создаем файл с рекомендациями
        rec_file = f"trading_recommendations_{timestamp}.txt"
        with open(rec_file, 'w', encoding='utf-8') as f:
            f.write("РЕКОМЕНДАЦИИ ПО КОИНТЕГРИРОВАННЫМ ПАРАМ\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Всего инструментов: {self.price_matrix.shape[1]}\n")
            f.write(f"Период анализа: {self.price_matrix.index.min().date()} - {self.price_matrix.index.max().date()}\n")
            f.write(f"Торговых дней: {self.price_matrix.shape[0]}\n")
            f.write(f"Найдено коинтегрированных пар: {len(pairs_df)}\n\n")
            
            f.write("КРИТЕРИИ ОТБОРА:\n")
            f.write(f"- Минимальная корреляция: {self.min_correlation}\n")
            f.write(f"- Макс p-value коинтеграции: {self.coint_pvalue_threshold}\n")
            f.write(f"- Макс p-value ADF теста: {self.adf_pvalue_threshold}\n")
            f.write(f"- Минимальное общих дней: {self.min_common_days}\n\n")
            
            f.write("ТОП-10 ПАР ДЛЯ ТОРГОВЛИ:\n")
            f.write("=" * 70 + "\n")
            
            for i, (_, row) in enumerate(pairs_df.head(10).iterrows(), 1):
                f.write(f"\n{i}. {row['ticker1']} ↔ {row['ticker2']}\n")
                f.write(f"   Корреляция: {row['correlation']:.3f}\n")
                f.write(f"   Коинтеграция p-value: {row.get('coint_pvalue', 'N/A'):.4f}\n")
                f.write(f"   ADF тест p-value: {row.get('adf_pvalue', 'N/A'):.4f}\n")
                f.write(f"   Hedge ratio: {row.get('hedge_ratio', 'N/A'):.4f}\n")
                f.write(f"   R² регрессии: {row.get('regression_r_squared', 'N/A'):.3f}\n")
                
                if 'half_life' in row and not pd.isna(row['half_life']):
                    f.write(f"   Half-life: {row['half_life']:.1f} дней\n")
                if 'hurst_exponent' in row and not pd.isna(row['hurst_exponent']):
                    hurst = row['hurst_exponent']
                    if hurst < 0.5:
                        f.write(f"   Экспонента Херста: {hurst:.3f} (mean-reverting)\n")
                    elif hurst > 0.5:
                        f.write(f"   Экспонента Херста: {hurst:.3f} (trending)\n")
                    else:
                        f.write(f"   Экспонента Херста: {hurst:.3f} (random walk)\n")
                
                f.write(f"   Стандартное отклонение спреда: {row.get('spread_std', 'N/A'):.3f}\n")
                f.write(f"   Рек. порог входа: {row.get('entry_threshold_std', 2.0)}σ\n")
                f.write(f"   Рек. порог выхода: {row.get('exit_threshold_std', 0.5)}σ\n")
        
        print(f"💾 Рекомендации сохранены: {rec_file}")
        
        # 3. Создаем файл со статистикой
        stats_file = f"cointegration_stats_{timestamp}.txt"
        with open(stats_file, 'w') as f:
            f.write("СТАТИСТИКА АНАЛИЗА КОИНТЕГРАЦИИ\n")
            f.write("=" * 50 + "\n")
            
            stats = {
                'timestamp': timestamp,
                'total_instruments': self.price_matrix.shape[1],
                'trading_days': self.price_matrix.shape[0],
                'cointegrated_pairs_found': len(pairs_df),
                'min_correlation': self.min_correlation,
                'coint_pvalue_threshold': self.coint_pvalue_threshold,
                'adf_pvalue_threshold': self.adf_pvalue_threshold,
                'min_common_days': self.min_common_days,
                'pairs_file': pairs_file,
                'recommendations_file': rec_file
            }
            
            for key, value in stats.items():
                f.write(f"{key:30}: {value}\n")
        
        print(f"📊 Статистика сохранена: {stats_file}")
        
        return {
            'pairs_file': pairs_file,
            'recommendations_file': rec_file,
            'stats_file': stats_file
        }
    
    def print_summary(self, pairs: List[Dict], files: dict):
        """Выводит итоговую сводку"""
        print("\n" + "=" * 80)
        print("🎯 ИТОГИ АНАЛИЗА КОИНТЕГРАЦИИ")
        print("=" * 80)
        
        if not pairs:
            print("❌ Не найдено коинтегрированных пар")
            return
        
        pairs_df = pd.DataFrame(pairs)
        
        print(f"📊 Найдено {len(pairs_df)} коинтегрированных пар со стационарным спредом")
        
        # Общая статистика
        print(f"\n📈 Общая статистика:")
        print(f"   Средняя корреляция: {pairs_df['correlation'].mean():.3f}")
        print(f"   Средний p-value коинтеграции: {pairs_df['coint_pvalue'].mean():.4f}")
        print(f"   Средний p-value ADF теста: {pairs_df['adf_pvalue'].mean():.4f}")
        print(f"   Средний hedge ratio: {pairs_df['hedge_ratio'].mean():.3f}")
        
        # Топ пар по качеству
        print(f"\n🏆 ТОП-3 пары по качеству:")
        
        for i, (_, row) in enumerate(pairs_df.head(3).iterrows(), 1):
            print(f"\n   {i}. {row['ticker1']} ↔ {row['ticker2']}")
            print(f"      Корреляция: {row['correlation']:.3f}")
            print(f"      Коинтеграция: p={row.get('coint_pvalue', 'N/A'):.4f}")
            print(f"      ADF тест: p={row.get('adf_pvalue', 'N/A'):.4f}")
            print(f"      Hedge ratio: {row.get('hedge_ratio', 'N/A'):.4f}")
            
            if 'half_life' in row and not pd.isna(row['half_life']):
                if row['half_life'] < np.inf:
                    print(f"      Half-life: {row['half_life']:.1f} дней")
            
            if 'spread_std' in row:
                print(f"      Std спреда: {row['spread_std']:.3f}")
        
        # Распределение по типам
        if 'ticker1_type' in pairs_df.columns:
            print(f"\n📊 Распределение по типам пар:")
            type_counts = pairs_df.apply(
                lambda x: f"{x['ticker1_type']}-{x['ticker2_type']}", axis=1
            ).value_counts()
            
            for pair_type, count in type_counts.head(5).items():
                print(f"   {pair_type:15}: {count} пар")
        
        print(f"\n💾 Файлы результатов:")
        for key, value in files.items():
            print(f"   {key:25}: {value}")
        
        print(f"\n🎯 Следующие шаги:")
        print(f"   1. Проанализировать {files['pairs_file']} для выбора пар")
        print(f"   2. Настроить параметры входа/выхода на основе half-life и волатильности")
        print(f"   3. Реализовать скринер спреда для выбранных пар")
        print("=" * 80)
    
    def run(self):
        """Основной метод запуска"""
        print("=" * 80)
        print("🔬 АНАЛИЗ КОИНТЕГРАЦИИ ДЛЯ СТАТИСТИЧЕСКОГО АРБИТРАЖА")
        print("Используются: Engle-Granger тест + ADF тест + линейная регрессия")
        print("=" * 80)
        
        # 1. Загружаем данные
        price_matrix, metadata = self.load_data()
        if price_matrix is None:
            return
        
        # 2. Находим коинтегрированные пары
        pairs = self.find_all_pairs()
        
        if not pairs:
            print("❌ Не найдено коинтегрированных пар")
            print("   Попробуйте изменить параметры:")
            print("   - Уменьшить min_correlation")
            print("   - Увеличить coint_pvalue_threshold")
            print("   - Использовать больше инструментов")
            return
        
        # 3. Сохраняем результаты
        files = self.save_results(pairs)
        
        # 4. Выводим сводку
        self.print_summary(pairs, files)

def main():
    """Точка входа"""
    try:
        # Настройки можно менять в зависимости от требований
        finder = CointegratedPairsFinder(
            min_correlation=0.65,           # Чуть ниже для большего охвата
            coint_pvalue_threshold=0.05,    # Стандартный 5% уровень значимости
            adf_pvalue_threshold=0.05,      # Стандартный 5% уровень значимости
            min_common_days=100             # Достаточно для статистики
        )
        finder.run()
        
    except KeyboardInterrupt:
        print("\n⏹️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
