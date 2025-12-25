#!/usr/bin/env python3
"""
Скрипт для получения списка акций и облигаций российского фондового рынка с Tinkoff Invest API.
Шаг 1 в пайплайне статистического арбитража.
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь для импорта модулей
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from tinkoff.invest import Client, InstrumentStatus
from src.utils.logger import log, log_api_call

# Загружаем переменные окружения
load_dotenv()

class InstrumentFetcherRF:
    """Класс для получения инструментов российского фондового рынка с Tinkoff Invest API"""
    
    # Коды бирж для российского фондового рынка
    RUSSIAN_EXCHANGES = ['MOEX', 'SPBX', 'SPB']  # Московская биржа, СПБ биржа
    
    def __init__(self):
        self.token = os.getenv('INVEST_TOKEN')
        if not self.token or "ваш_токен" in self.token:
            log.error("❌ Токен Tinkoff API не найден или не настроен в .env файле")
            log.error("   Проверьте переменную INVEST_TOKEN в файле .env")
            sys.exit(1)
        
        log.info("🚀 Инициализация InstrumentFetcherRF (только РФ фондовый рынок)")
    
    def fetch_shares(self):
        """Получение списка акций"""
        try:
            log_api_call("instruments", "shares")
            start_time = datetime.now()
            
            with Client(self.token) as client:
                # Запрашиваем базовый список инструментов, доступных для торговли через API
                response = client.instruments.shares(
                    instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
                )
                
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log.info(f"✅ Получено {len(response.instruments)} акций за {duration_ms:.1f} мс")
            log_api_call("instruments", "shares", duration_ms, count=len(response.instruments))
            
            return response.instruments
            
        except Exception as e:
            log.error(f"❌ Ошибка получения акций: {e}")
            return []
    
    def fetch_bonds(self):
        """Получение списка облигаций"""
        try:
            log_api_call("instruments", "bonds")
            start_time = datetime.now()
            
            with Client(self.token) as client:
                # Запрашиваем базовый список инструментов, доступных для торговли через API
                response = client.instruments.bonds(
                    instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
                )
                
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log.info(f"✅ Получено {len(response.instruments)} облигаций за {duration_ms:.1f} мс")
            log_api_call("instruments", "bonds", duration_ms, count=len(response.instruments))
            
            return response.instruments
            
        except Exception as e:
            log.error(f"❌ Ошибка получения облигаций: {e}")
            return []
    
    def filter_russian_instruments(self, instruments):
        """Фильтрация инструментов: только российский фондовый рынок и доступные для торговли через API"""
        filtered = []
        for instr in instruments:
            # Проверяем, доступен ли инструмент для торговли через API
            if not (hasattr(instr, 'api_trade_available_flag') and instr.api_trade_available_flag):
                continue
            
            # Проверяем, что инструмент торгуется на российской бирже
            if hasattr(instr, 'exchange'):
                # Проверяем, что биржа в списке российских
                if instr.exchange in self.RUSSIAN_EXCHANGES:
                    filtered.append(instr)
                else:
                    # Логируем отфильтрованные инструменты для отладки
                    log.debug(f"Отфильтрован инструмент {instr.ticker}: биржа {instr.exchange}")
            else:
                # Если нет информации о бирже, пропускаем
                log.debug(f"Инструмент {instr.ticker} без информации о бирже")
        
        log.info(f"📊 После фильтрации по РФ рынку: {len(filtered)} из {len(instruments)} инструментов")
        return filtered
    
    def instruments_to_dataframe(self, shares, bonds):
        """Конвертация инструментов в DataFrame с информацией о бирже"""
        data = []
        
        # Обработка акций
        for share in shares:
            data.append({
                'ticker': share.ticker,
                'name': share.name,
                'figi': share.figi,
                'type': 'share',
                'currency': share.currency,
                'lot': share.lot,
                'min_price_increment': self._quotation_to_float(share.min_price_increment) 
                if hasattr(share, 'min_price_increment') else None,
                'uid': share.uid if hasattr(share, 'uid') else None,
                'exchange': share.exchange if hasattr(share, 'exchange') else 'N/A',
                'sector': share.sector if hasattr(share, 'sector') else 'N/A',
                'country_of_risk': share.country_of_risk if hasattr(share, 'country_of_risk') else 'N/A'
            })
        
        # Обработка облигаций
        for bond in bonds:
            data.append({
                'ticker': bond.ticker,
                'name': bond.name,
                'figi': bond.figi,
                'type': 'bond',
                'currency': bond.currency,
                'lot': bond.lot,
                'min_price_increment': self._quotation_to_float(bond.min_price_increment) 
                if hasattr(bond, 'min_price_increment') else None,
                'uid': bond.uid if hasattr(bond, 'uid') else None,
                'exchange': bond.exchange if hasattr(bond, 'exchange') else 'N/A',
                'country_of_risk': bond.country_of_risk if hasattr(bond, 'country_of_risk') else 'N/A',
                'nominal': self._quotation_to_float(bond.nominal) if hasattr(bond, 'nominal') else None
            })
        
        df = pd.DataFrame(data)
        log.info(f"📁 Создан DataFrame с {len(df)} инструментами")
        return df
    
    def _quotation_to_float(self, quotation):
        """Конвертация Quotation в float (как в существующем коде)"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def save_to_csv(self, df, filename=None):
        """Сохранение DataFrame в CSV файл в корневой папке проекта"""
        if df.empty:
            log.warning("⚠️  DataFrame пуст, нечего сохранять")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"instruments_rf_{timestamp}.csv"
        
        # Сохраняем в корневую папку проекта
        filepath = Path(project_root) / filename
        df.to_csv(filepath, index=False, encoding='utf-8')
        log.info(f"💾 Данные сохранены в {filepath} ({len(df)} записей)")
        
        return filepath
    
    def run(self):
        """Основной метод запуска"""
        log.info("🎯 Начало получения списка инструментов российского фондового рынка (акции и облигации)")
        
        # Получаем инструменты
        shares = self.fetch_shares()
        bonds = self.fetch_bonds()
        
        # Фильтруем (только российский рынок и доступные для API-торговли)
        filtered_shares = self.filter_russian_instruments(shares)
        filtered_bonds = self.filter_russian_instruments(bonds)
        
        # Конвертируем в DataFrame
        df = self.instruments_to_dataframe(filtered_shares, filtered_bonds)
        
        if df.empty:
            log.error("❌ Не удалось получить инструменты. Проверьте токен и подключение.")
            return None
        
        # Сохраняем в CSV в корневую папку
        csv_file = self.save_to_csv(df)
        
        # Выводим статистику
        self.print_statistics(df)
        
        return csv_file
    
    def print_statistics(self, df):
        """Вывод статистики по инструментам"""
        print("\n" + "="*60)
        print("📊 СТАТИСТИКА ПОЛУЧЕННЫХ ИНСТРУМЕНТОВ (РФ ФОНДОВЫЙ РЫНОК)")
        print("="*60)
        
        # Общая статистика
        print(f"Всего инструментов: {len(df)}")
        print(f"Акций: {len(df[df['type'] == 'share'])}")
        print(f"Облигаций: {len(df[df['type'] == 'bond'])}")
        
        # По биржам
        if 'exchange' in df.columns:
            print("\nПо биржам:")
            for exchange, count in df['exchange'].value_counts().items():
                print(f"  {exchange}: {count} инструментов")
        
        # По валютам
        if 'currency' in df.columns:
            print("\nПо валютам:")
            for currency, count in df['currency'].value_counts().items():
                print(f"  {currency}: {count} инструментов")
        
        # Примеры инструментов
        print("\nПримеры инструментов:")
        for i, (_, row) in enumerate(df.head(5).iterrows()):
            print(f"  {i+1}. {row['ticker']} - {row['name'][:30]}... ({row['type']}, {row['exchange']})")
        
        if len(df) > 5:
            print(f"  ... и еще {len(df) - 5} инструментов")
        
        print("="*60)

def main():
    """Точка входа"""
    print("🔍 СКРИПТ ПОЛУЧЕНИЯ ИНСТРУМЕНТОВ РФ ФОНДОВОГО РЫНКА TINKOFF INVEST")
    print("Типы: акции и облигации, только MOEX/SPB биржи, доступные для торговли через API")
    print("="*60)
    
    try:
        fetcher = InstrumentFetcherRF()
        result_file = fetcher.run()
        
        if result_file:
            print(f"\n✅ СКРИПТ УСПЕШНО ВЫПОЛНЕН!")
            print(f"📁 Файл с инструментами: {result_file}")
            print(f"📁 Расположение: корневая папка проекта")
            print("\n📋 Для просмотра первых строк файла выполните:")
            print(f"   head -20 {result_file.name}")
            print("\n📋 Для просмотра структуры файла:")
            print(f"   wc -l {result_file.name} && echo 'Колонки:' && head -1 {result_file.name} | tr ',' '\\n' | nl")
            print("\n🎯 Следующий шаг: использовать этот файл для загрузки исторических данных")
        else:
            print("\n❌ СКРИПТ ЗАВЕРШИЛСЯ С ОШИБКОЙ")
            print("   Проверьте логи выше и настройте .env файл")
            
    except KeyboardInterrupt:
        print("\n⏹️  Прервано пользователем")
    except Exception as e:
        log.error(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
