#!/usr/bin/env python3
"""
Бэктестер стратегии парного арбитража на РЕАЛЬНЫХ данных (ИСПРАВЛЕННЫЙ)
Исправлен расчет доходности - учитывает реальный капитал
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Создаем папку для результатов
results_dir = Path(__file__).parent / "results"
results_dir.mkdir(exist_ok=True)

class FixedPairBacktester:
    """Бэктестер парного арбитража с правильным расчетом капитала"""
    
    def __init__(self, ticker1: str, ticker2: str, hedge_ratio: float = 1.1950,
                 entry_threshold: float = 2.0, exit_threshold: float = 0.5,
                 lookback_window: int = 60, margin_requirement: float = 1.3):
        """
        Инициализация бэктестера
        
        Args:
            ticker1: Первый тикер (TGKJ)
            ticker2: Второй тикер (ALRS)
            hedge_ratio: Коэффициент хеджирования (1.1950 из анализа)
            entry_threshold: Порог входа в сигмах (2.0)
            exit_threshold: Порог выхода в сигмах (0.5)
            lookback_window: Окно для расчета скользящих статистик (60 дней)
            margin_requirement: Требование к марже для коротких позиций (130%)
        """
        self.ticker1 = ticker1
        self.ticker2 = ticker2
        self.hedge_ratio = hedge_ratio
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.lookback_window = lookback_window
        self.margin_requirement = margin_requirement
        
        print(f"🤖 Бэктестер парного арбитража (ИСПРАВЛЕННЫЙ)")
        print(f"📊 Пара: {ticker1} ↔ {ticker2}")
        print(f"   Hedge ratio: {hedge_ratio}")
        print(f"   Порог входа: {entry_threshold}σ")
        print(f"   Порог выхода: {exit_threshold}σ")
        print(f"   Окно анализа: {lookback_window} дней")
        print(f"   Требование маржи: {margin_requirement * 100:.0f}%")
    
    def load_data(self):
        """Загружает данные из сохраненных файлов"""
        data_dir = Path(__file__).parent / "data"
        
        file1 = data_dir / f"{self.ticker1}_historical.csv"
        file2 = data_dir / f"{self.ticker2}_historical.csv"
        
        if not file1.exists() or not file2.exists():
            print(f"❌ Файлы данных не найдены!")
            print(f"   Сначала запустите: python tests/strategies/load_pair_data.py {self.ticker1} {self.ticker2}")
            return None, None
        
        print(f"\n📂 Загружаем данные из файлов...")
        
        df1 = pd.read_csv(file1, index_col='date', parse_dates=True)
        df2 = pd.read_csv(file2, index_col='date', parse_dates=True)
        
        # Находим общие даты
        common_dates = df1.index.intersection(df2.index)
        df1 = df1.loc[common_dates]
        df2 = df2.loc[common_dates]
        
        print(f"✅ Данные загружены:")
        print(f"   Период: {df1.index.min().date()} - {df1.index.max().date()}")
        print(f"   Торговых дней: {len(df1)}")
        
        return df1, df2
    
    def calculate_spread(self, df1: pd.DataFrame, df2: pd.DataFrame):
        """Рассчитывает спред и скользящие статистики"""
        print(f"\n📈 Рассчитываем спред...")
        
        # Цены закрытия
        price1 = df1['close']
        price2 = df2['close']
        
        # Спред
        spread = price1 - self.hedge_ratio * price2
        
        # Скользящие статистики (без look-ahead bias!)
        spread_mean = spread.rolling(window=self.lookback_window, min_periods=30).mean()
        spread_std = spread.rolling(window=self.lookback_window, min_periods=30).std()
        
        # Z-score (нормализованный спред)
        z_score = (spread - spread_mean) / spread_std
        
        return spread, spread_mean, spread_std, z_score
    
    def generate_signals(self, z_score: pd.Series):
        """Генерирует торговые сигналы на основе z-score"""
        print(f"\n🎯 Генерируем торговые сигналы...")
        
        signals = pd.Series(0, index=z_score.index, dtype=int)
        position = 0
        trades = []
        
        for i in range(self.lookback_window, len(z_score)):
            current_z = z_score.iloc[i]
            
            if pd.isna(current_z):
                continue
            
            if position == 0:
                # Нет позиции - ищем вход
                if current_z < -self.entry_threshold:
                    signals.iloc[i] = 1
                    position = 1
                    trades.append({
                        'entry_date': z_score.index[i],
                        'action': 'BUY_SPREAD',
                        'entry_z': current_z,
                        'position': position
                    })
                elif current_z > self.entry_threshold:
                    signals.iloc[i] = -1
                    position = -1
                    trades.append({
                        'entry_date': z_score.index[i],
                        'action': 'SELL_SPREAD',
                        'entry_z': current_z,
                        'position': position
                    })
            
            elif position == 1:
                if current_z > -self.exit_threshold:
                    signals.iloc[i] = 0
                    position = 0
                    trades[-1]['exit_date'] = z_score.index[i]
                    trades[-1]['exit_z'] = current_z
                    trades[-1]['duration_days'] = (trades[-1]['exit_date'] - trades[-1]['entry_date']).days
            
            elif position == -1:
                if current_z < self.exit_threshold:
                    signals.iloc[i] = 0
                    position = 0
                    trades[-1]['exit_date'] = z_score.index[i]
                    trades[-1]['exit_z'] = current_z
                    trades[-1]['duration_days'] = (trades[-1]['exit_date'] - trades[-1]['entry_date']).days
        
        # Если позиция осталась открытой в конце
        if position != 0 and trades:
            last_date = z_score.index[-1]
            trades[-1]['exit_date'] = last_date
            trades[-1]['exit_z'] = z_score.iloc[-1]
            trades[-1]['duration_days'] = (last_date - trades[-1]['entry_date']).days
        
        print(f"   Сгенерировано сделок: {len(trades)}")
        
        return signals, pd.DataFrame(trades)
    
    def calculate_capital_required(self, action: str, price1: float, price2: float) -> float:
        """
        Рассчитывает требуемый капитал для сделки
        
        Args:
            action: 'BUY_SPREAD' или 'SELL_SPREAD'
            price1: Цена первого инструмента
            price2: Цена второго инструмента
            
        Returns:
            Требуемый капитал
        """
        if action == 'BUY_SPREAD':
            # Long TGKJ (полная стоимость) + Short ALRS (требуется маржа)
            return price1 + self.margin_requirement * self.hedge_ratio * price2
        else:  # 'SELL_SPREAD'
            # Short TGKJ (требуется маржа) + Long ALRS (полная стоимость)
            return self.margin_requirement * price1 + self.hedge_ratio * price2
    
    def calculate_returns(self, df1: pd.DataFrame, df2: pd.DataFrame, 
                         signals: pd.Series, trades: pd.DataFrame):
        """Рассчитывает доходность стратегии с правильным учетом капитала"""
        if trades.empty:
            print("❌ Нет сделок для анализа доходности")
            return pd.Series(), pd.Series(), trades
        
        print(f"\n💰 Рассчитываем доходность (с учетом реального капитала)...")
        
        # Рассчитываем метрики для сделок
        trades_with_metrics = trades.copy()
        
        for idx, trade in trades_with_metrics.iterrows():
            # Цены на входе и выходе
            entry_date = trade['entry_date']
            exit_date = trade['exit_date']
            
            price1_entry = df1.loc[entry_date, 'close']
            price2_entry = df2.loc[entry_date, 'close']
            price1_exit = df1.loc[exit_date, 'close']
            price2_exit = df2.loc[exit_date, 'close']
            
            # Рассчитываем PnL
            if trade['action'] == 'BUY_SPREAD':
                # Long spread: купили TGKJ, продали ALRS
                pnl = (price1_exit - price1_entry) - self.hedge_ratio * (price2_exit - price2_entry)
            else:  # 'SELL_SPREAD'
                # Short spread: продали TGKJ, купили ALRS
                pnl = (price1_entry - price1_exit) - self.hedge_ratio * (price2_entry - price2_exit)
            
            # РЕАЛЬНЫЙ требуемый капитал
            capital_required = self.calculate_capital_required(
                trade['action'], price1_entry, price2_entry
            )
            
            # Реальная доходность
            return_pct = (pnl / capital_required) * 100 if capital_required > 0 else 0
            
            # Заполняем данные
            trades_with_metrics.loc[idx, 'price1_entry'] = price1_entry
            trades_with_metrics.loc[idx, 'price2_entry'] = price2_entry
            trades_with_metrics.loc[idx, 'price1_exit'] = price1_exit
            trades_with_metrics.loc[idx, 'price2_exit'] = price2_exit
            trades_with_metrics.loc[idx, 'pnl'] = pnl
            trades_with_metrics.loc[idx, 'capital_required'] = capital_required
            trades_with_metrics.loc[idx, 'return_pct'] = return_pct
            
            # Годовая доходность
            if trade['duration_days'] > 0:
                annualized_return = ((1 + return_pct/100) ** (365/trade['duration_days']) - 1) * 100
                trades_with_metrics.loc[idx, 'annualized_return'] = annualized_return
        
        # Рассчитываем ежедневные доходности стратегии
        returns1 = df1['close'].pct_change()
        returns2 = df2['close'].pct_change()
        spread_returns = returns1 - self.hedge_ratio * returns2
        
        strategy_returns = pd.Series(0.0, index=signals.index)
        position = 0
        
        for i in range(len(signals)):
            if signals.iloc[i] != 0 and position == 0:
                position = signals.iloc[i]
            
            if position != 0:
                if position == 1:
                    strategy_returns.iloc[i] = spread_returns.iloc[i]
                else:  # position == -1
                    strategy_returns.iloc[i] = -spread_returns.iloc[i]
            
            if signals.iloc[i] == 0 and position != 0:
                position = 0
        
        # Кумулятивная доходность
        cumulative_returns = (1 + strategy_returns).cumprod() - 1
        
        # Общая статистика
        total_return = cumulative_returns.iloc[-1] * 100 if len(cumulative_returns) > 0 else 0
        
        # Sharpe Ratio
        if len(strategy_returns) > 0 and strategy_returns.std() > 0:
            sharpe_ratio = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # Максимальная просадка
        cumulative = (1 + strategy_returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        print(f"📊 РЕЗУЛЬТАТЫ СТРАТЕГИИ:")
        print(f"   Общая доходность: {total_return:.2f}%")
        print(f"   Количество сделок: {len(trades_with_metrics)}")
        
        if len(trades_with_metrics) > 0:
            win_rate = (trades_with_metrics['pnl'] > 0).sum() / len(trades_with_metrics) * 100
            avg_return = trades_with_metrics['return_pct'].mean()
            avg_duration = trades_with_metrics['duration_days'].mean()
            total_capital = trades_with_metrics['capital_required'].sum()
            total_pnl = trades_with_metrics['pnl'].sum()
            roi = total_pnl / total_capital * 100 if total_capital > 0 else 0
            
            print(f"   Процент прибыльных: {win_rate:.1f}%")
            print(f"   Средняя доходность сделки: {avg_return:.2f}%")
            print(f"   ROI (общий PnL / общий капитал): {roi:.2f}%")
            print(f"   Средняя длительность: {avg_duration:.1f} дней")
            print(f"   Sharpe Ratio: {sharpe_ratio:.2f}")
            print(f"   Максимальная просадка: {max_drawdown:.2f}%")
        
        return strategy_returns, cumulative_returns, trades_with_metrics
    
    def plot_results(self, df1: pd.DataFrame, df2: pd.DataFrame, 
                    spread: pd.Series, z_score: pd.Series,
                    signals: pd.Series, cumulative_returns: pd.Series,
                    trades: pd.DataFrame):
        """Создает графики результатов"""
        if trades.empty:
            print("⚠️  Нет сделок для построения графиков")
            return
        
        print(f"\n📊 Создаем графики результатов...")
        
        fig, axes = plt.subplots(5, 1, figsize=(16, 20))
        
        # 1. Цены инструментов
        axes[0].plot(df1.index, df1['close'], label=f'{self.ticker1}', alpha=0.7, linewidth=2)
        axes[0].plot(df2.index, df2['close'], label=f'{self.ticker2}', alpha=0.7, linewidth=2)
        axes[0].set_title(f'Цены инструментов: {self.ticker1} и {self.ticker2}', fontsize=14)
        axes[0].set_ylabel('Цена', fontsize=12)
        axes[0].legend(loc='upper left')
        axes[0].grid(True, alpha=0.3)
        
        # 2. Спред
        axes[1].plot(spread.index, spread, label='Спред', color='purple', alpha=0.7, linewidth=2)
        axes[1].axhline(y=spread.mean(), color='gray', linestyle='--', label='Среднее')
        axes[1].set_title(f'Спред: {self.ticker1} - {self.hedge_ratio:.4f} × {self.ticker2}', fontsize=14)
        axes[1].set_ylabel('Спред', fontsize=12)
        axes[1].legend(loc='upper left')
        axes[1].grid(True, alpha=0.3)
        
        # 3. Z-score с торговыми сигналами
        axes[2].plot(z_score.index, z_score, label='Z-score', color='blue', alpha=0.7, linewidth=1.5)
        axes[2].axhline(y=self.entry_threshold, color='red', linestyle='--', label=f'Вход ({self.entry_threshold}σ)')
        axes[2].axhline(y=-self.entry_threshold, color='red', linestyle='--')
        axes[2].axhline(y=self.exit_threshold, color='green', linestyle=':', label=f'Выход ({self.exit_threshold}σ)')
        axes[2].axhline(y=-self.exit_threshold, color='green', linestyle=':')
        axes[2].axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        
        # Отмечаем сделки
        for _, trade in trades.iterrows():
            if trade['action'] == 'BUY_SPREAD':
                axes[2].axvspan(trade['entry_date'], trade['exit_date'], 
                               alpha=0.2, color='green', label='Long Spread' if _ == 0 else "")
            else:  # 'SELL_SPREAD'
                axes[2].axvspan(trade['entry_date'], trade['exit_date'], 
                               alpha=0.2, color='red', label='Short Spread' if _ == 0 else "")
        
        axes[2].set_title('Z-score спреда и торговые сигналы', fontsize=14)
        axes[2].set_ylabel('Z-score', fontsize=12)
        handles, labels = axes[2].get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        axes[2].legend(by_label.values(), by_label.keys(), loc='upper left')
        axes[2].grid(True, alpha=0.3)
        
        # 4. Доходность стратегии
        axes[3].plot(cumulative_returns.index, cumulative_returns * 100, 
                    label='Стратегия', color='darkgreen', linewidth=2)
        axes[3].axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        axes[3].set_title('Кумулятивная доходность стратегии', fontsize=14)
        axes[3].set_ylabel('Доходность (%)', fontsize=12)
        axes[3].legend(loc='upper left')
        axes[3].grid(True, alpha=0.3)
        
        # 5. Доходность по сделкам
        if not trades.empty:
            trades_sorted = trades.sort_values('entry_date')
            axes[4].bar(range(len(trades_sorted)), trades_sorted['return_pct'], 
                       color=['green' if x > 0 else 'red' for x in trades_sorted['return_pct']],
                       alpha=0.7)
            axes[4].axhline(y=0, color='gray', linestyle='-', alpha=0.5)
            axes[4].set_title('Доходность отдельных сделок', fontsize=14)
            axes[4].set_xlabel('Номер сделки', fontsize=12)
            axes[4].set_ylabel('Доходность (%)', fontsize=12)
            axes[4].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Сохраняем график
        plot_file = results_dir / f"backtest_{self.ticker1}_{self.ticker2}_FIXED.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.show()
        
        print(f"💾 График сохранен в: {plot_file}")
    
    def save_results(self, trades: pd.DataFrame, cumulative_returns: pd.Series):
        """Сохраняет результаты в файлы"""
        if trades.empty:
            print("⚠️  Нет результатов для сохранения")
            return
        
        # Сохраняем сделки
        trades_file = results_dir / f"trades_{self.ticker1}_{self.ticker2}_FIXED.csv"
        trades.to_csv(trades_file, index=False)
        print(f"💾 Сделки сохранены в: {trades_file}")
        
        # Создаем отчет
        report_file = results_dir / f"report_{self.ticker1}_{self.ticker2}_FIXED.txt"
        with open(report_file, 'w') as f:
            f.write(f"ОТЧЕТ ПО БЭКТЕСТУ (ИСПРАВЛЕННЫЙ РАСЧЕТ)\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Пара: {self.ticker1} ↔ {self.ticker2}\n")
            f.write(f"Hedge ratio: {self.hedge_ratio}\n")
            f.write(f"Порог входа: {self.entry_threshold}σ\n")
            f.write(f"Порог выхода: {self.exit_threshold}σ\n")
            f.write(f"Окно анализа: {self.lookback_window} дней\n")
            f.write(f"Требование маржи: {self.margin_requirement * 100:.0f}%\n\n")
            
            f.write("СТАТИСТИКА СДЕЛОК:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Всего сделок: {len(trades)}\n")
            
            if len(trades) > 0:
                win_rate = (trades['pnl'] > 0).sum() / len(trades) * 100
                avg_return = trades['return_pct'].mean()
                roi = trades['pnl'].sum() / trades['capital_required'].sum() * 100
                
                f.write(f"Процент прибыльных: {win_rate:.1f}%\n")
                f.write(f"Средняя доходность сделки: {avg_return:.2f}%\n")
                f.write(f"ROI (общий PnL / общий капитал): {roi:.2f}%\n")
                f.write(f"Средняя длительность: {trades['duration_days'].mean():.1f} дней\n\n")
                
                f.write("ЛУЧШИЕ СДЕЛКИ:\n")
                f.write("-" * 40 + "\n")
                best_trades = trades.nlargest(5, 'return_pct')
                for _, trade in best_trades.iterrows():
                    f.write(f"{trade['action']}: {trade['return_pct']:.2f}% за {trade['duration_days']} дней "
                           f"(капитал: {trade['capital_required']:.2f})\n")
                
                f.write("\nХУДШИЕ СДЕЛКИ:\n")
                f.write("-" * 40 + "\n")
                worst_trades = trades.nsmallest(5, 'return_pct')
                for _, trade in worst_trades.iterrows():
                    f.write(f"{trade['action']}: {trade['return_pct']:.2f}% за {trade['duration_days']} дней "
                           f"(капитал: {trade['capital_required']:.2f})\n")
        
        print(f"📋 Отчет сохранен в: {report_file}")
    
    def run_backtest(self):
        """Запускает полный бэктест с исправленным расчетом"""
        print(f"\n{'='*70}")
        print(f"🚀 ЗАПУСК БЭКТЕСТА (ИСПРАВЛЕННЫЙ РАСЧЕТ)")
        print(f"📊 ПАРА: {self.ticker1} ↔ {self.ticker2}")
        print(f"{'='*70}")
        
        # 1. Загружаем данные
        df1, df2 = self.load_data()
        if df1 is None or df2 is None:
            print("❌ Не удалось загрузить данные")
            return None
        
        # 2. Рассчитываем спред и статистики
        spread, spread_mean, spread_std, z_score = self.calculate_spread(df1, df2)
        
        # 3. Генерируем сигналы
        signals, trades = self.generate_signals(z_score)
        
        if trades.empty:
            print("❌ Нет торговых сигналов в выбранный период")
            return None
        
        # 4. Рассчитываем доходность с правильным учетом капитала
        strategy_returns, cumulative_returns, trades_with_metrics = self.calculate_returns(
            df1, df2, signals, trades
        )
        
        # 5. Создаем графики
        self.plot_results(df1, df2, spread, z_score, signals, 
                         cumulative_returns, trades_with_metrics)
        
        # 6. Сохраняем результаты
        self.save_results(trades_with_metrics, cumulative_returns)
        
        print(f"\n{'='*70}")
        print(f"🎯 БЭКТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        print(f"📊 Результаты с РЕАЛЬНЫМ учетом капитала")
        print(f"{'='*70}")
        
        results = {
            'total_trades': len(trades_with_metrics),
            'win_rate': (trades_with_metrics['pnl'] > 0).sum() / len(trades_with_metrics) * 100,
            'avg_return': trades_with_metrics['return_pct'].mean(),
            'roi': trades_with_metrics['pnl'].sum() / trades_with_metrics['capital_required'].sum() * 100,
            'total_return': cumulative_returns.iloc[-1] * 100 if len(cumulative_returns) > 0 else 0,
            'trades': trades_with_metrics,
            'cumulative_returns': cumulative_returns
        }
        
        return results

def main():
    """Основная функция"""
    print("🤖 Бэктестер парного арбитража (ИСПРАВЛЕННЫЙ РАСЧЕТ)")
    print("=" * 70)
    
    # Параметры для TGKJ ↔ ALRS
    ticker1 = "TGKJ"
    ticker2 = "ALRS"
    hedge_ratio = 1.1950
    entry_threshold = 2.0  # σ
    exit_threshold = 0.5   # σ
    lookback_window = 60   # дней для расчета статистик
    margin_requirement = 1.3  # 130% маржа для коротких позиций
    
    print(f"📊 ПАРА: {ticker1} ↔ {ticker2}")
    print(f"   Hedge ratio: {hedge_ratio}")
    print(f"   Порог входа: {entry_threshold}σ")
    print(f"   Порог выхода: {exit_threshold}σ")
    print(f"   Окно анализа: {lookback_window} дней")
    print(f"   Требование маржи: {margin_requirement * 100:.0f}%")
    print("=" * 70)
    
    # Создаем бэктестер
    backtester = FixedPairBacktester(
        ticker1=ticker1,
        ticker2=ticker2,
        hedge_ratio=hedge_ratio,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        lookback_window=lookback_window,
        margin_requirement=margin_requirement
    )
    
    # Запускаем бэктест
    results = backtester.run_backtest()
    
    if results:
        print(f"\n📈 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
        print(f"   Всего сделок: {results['total_trades']}")
        print(f"   Процент прибыльных: {results['win_rate']:.1f}%")
        print(f"   Средняя доходность сделки: {results['avg_return']:.2f}%")
        print(f"   ROI (общий PnL / общий капитал): {results['roi']:.2f}%")
        print(f"   Общая доходность стратегии: {results['total_return']:.2f}%")
        print(f"\n📁 Результаты сохранены в папке: tests/strategies/results/")
        print(f"   (файлы с суффиксом _FIXED)")
    else:
        print("❌ Бэктест не удался")

if __name__ == "__main__":
    main()
