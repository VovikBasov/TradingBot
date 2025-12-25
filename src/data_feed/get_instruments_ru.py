#!/usr/bin/env python3
"""
Скрипт для получения списка акций и облигаций с country_of_risk = 'RU'
Точная фильтрация для российского рынка.
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

# Загружаем переменные окружения
load_dotenv()

# Создаем простой логгер
class SimpleLogger:
    @staticmethod
    def info(msg):
        print(f"INFO: {msg}")
    
    @staticmethod
    def error(msg):
        print(f"ERROR: {msg}")
    
    @staticmethod
    def warning(msg):
        print(f"WARNING: {msg}")
    
    @staticmethod
    def debug(msg):
        print(f"DEBUG: {msg}")

log = SimpleLogger()

class InstrumentFetcherRU:
    """Класс для получения инструментов с country_of_risk = 'RU'"""
    
    def __init__(self):
        self.token = os.getenv('INVEST_TOKEN')
        if not self.token or "ваш_токен" in self.token:
            log.error("❌ Токен Tinkoff API не найден или не настроен в .env файле")
            sys.exit(1)
        
        log.info("🚀 Инициализация InstrumentFetcherRU (страна риска = RU)")
    
    def fetch_shares(self):
        """Получение списка акций"""
        try:
            start_time = datetime.now()
            
            with Client(self.token) as client:
                response = client.instruments.shares(
                    instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
                )
                
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log.info(f"✅ Получено {len(response.instruments)} акций за {duration_ms:.1f} мс")
            
            return response.instruments
            
        except Exception as e:
            log.error(f"❌ Ошибка получения акций: {e}")
            return []
    
    def fetch_bonds(self):
        """Получение списка облигаций"""
        try:
            start_time = datetime.now()
            
            with Client(self.token) as client:
                response = client.instruments.bonds(
                    instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
                )
                
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log.info(f"✅ Получено {len(response.instruments)} облигаций за {duration_ms:.1f} мс")
            
            return response.instruments
            
        except Exception as e:
            log.error(f"❌ Ошибка получения облигаций: {e}")
            return []
    
    def filter_ru_instruments(self, instruments):
        """Фильтрация инструментов: только country_of_risk = 'RU' и доступные для торговли через API"""
        filtered = []
        not_ru_count = 0
        not_api_count = 0
        
        for instr in instruments:
            # Проверяем, доступен ли инструмент для торговли через API
            if not (hasattr(instr, 'api_trade_available_flag') and instr.api_trade_available_flag):
                not_api_count += 1
                continue
            
            # Проверяем страну риска (основной критерий - строго 'RU')
            if hasattr(instr, 'country_of_risk'):
                # Приводим к строке и проверяем
                country = str(instr.country_of_risk).strip()
                if country.upper() == 'RU':
                    filtered.append(instr)
                else:
                    not_ru_count += 1
                    log.debug(f"Отфильтрован {instr.ticker}: country_of_risk='{country}'")
            else:
                # Если нет country_of_risk, пропускаем
                not_ru_count += 1
                log.debug(f"Отфильтрован {instr.ticker}: нет country_of_risk")
        
        log.info(f"📊 Фильтрация: {len(filtered)} из {len(instruments)} инструментов")
        log.info(f"   Не прошли фильтр country_of_risk='RU': {not_ru_count}")
        log.info(f"   Не доступны для API-торговли: {not_api_count}")
        
        return filtered
    
    def instruments_to_dataframe(self, shares, bonds):
        """Конвертация инструментов в DataFrame"""
        data = []
        
        # Обработка акций
        for share in shares:
            data.append({
                'ticker': share.ticker,
                'name': share.name,
                'figi': share.figi,
                'type': 'share',
                'currency': getattr(share, 'currency', 'N/A'),
                'lot': share.lot,
                'min_price_increment': self._quotation_to_float(getattr(share, 'min_price_increment', None)),
                'uid': getattr(share, 'uid', None),
                'exchange': getattr(share, 'exchange', 'N/A'),
                'sector': getattr(share, 'sector', 'N/A'),
                'country_of_risk': getattr(share, 'country_of_risk', 'N/A'),
                'class_code': getattr(share, 'class_code', 'N/A')
            })
        
        # Обработка облигаций
        for bond in bonds:
            data.append({
                'ticker': bond.ticker,
                'name': bond.name,
                'figi': bond.figi,
                'type': 'bond',
                'currency': getattr(bond, 'currency', 'N/A'),
                'lot': bond.lot,
                'min_price_increment': self._quotation_to_float(getattr(bond, 'min_price_increment', None)),
                'uid': getattr(bond, 'uid', None),
                'exchange': getattr(bond, 'exchange', 'N/A'),
                'country_of_risk': getattr(bond, 'country_of_risk', 'N/A'),
                'nominal': self._quotation_to_float(getattr(bond, 'nominal', None)),
                'class_code': getattr(bond, 'class_code', 'N/A')
            })
        
        df = pd.DataFrame(data)
        log.info(f"📁 Создан DataFrame с {len(df)} инструментами")
        return df
    
    def _quotation_to_float(self, quotation):
        """Конвертация Quotation в float"""
        if quotation is None:
            return None
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
            filename = f"instruments_ru_{timestamp}.csv"
        
        # Сохраняем в корневую папку проекта
        filepath = Path(project_root) / filename
        df.to_csv(filepath, index=False, encoding='utf-8')
        log.info(f"💾 Данные сохранены в {filepath} ({len(df)} записей)")
        
        return filepath
    
    def run(self):
        """Основной метод запуска"""
        log.info("🎯 Начало получения инструментов с country_of_risk = 'RU'")
        
        # Получаем инструменты
        shares = self.fetch_shares()
        bonds = self.fetch_bonds()
        
        # Фильтруем (только country_of_risk = 'RU' и доступные для API-торговли)
        filtered_shares = self.filter_ru_instruments(shares)
        filtered_bonds = self.filter_ru_instruments(bonds)
        
        # Конвертируем в DataFrame
        df = self.instruments_to_dataframe(filtered_shares, filtered_bonds)
        
        if df.empty:
            log.error("❌ Не удалось получить инструменты.")
            log.error("   Возможные причины:")
            log.error("   1. Токен API не работает")
            log.error("   2. В API нет инструментов с country_of_risk='RU'")
            log.error("   3. Проблема с подключением к интернету")
            return None
        
        # Сохраняем в CSV в корневую папку
        csv_file = self.save_to_csv(df)
        
        # Выводим статистику
        self.print_statistics(df)
        
        return csv_file
    
    def print_statistics(self, df):
        """Вывод статистики по инструментам"""
        print("\n" + "="*70)
        print("📊 СТАТИСТИКА ПОЛУЧЕННЫХ ИНСТРУМЕНТОВ (country_of_risk = 'RU')")
        print("="*70)
        
        # Общая статистика
        print(f"Всего инструментов: {len(df)}")
        print(f"Акций: {len(df[df['type'] == 'share'])}")
        print(f"Облигаций: {len(df[df['type'] == 'bond'])}")
        
        # По биржам
        if 'exchange' in df.columns and not df['exchange'].isnull().all():
            print("\nТоп-10 бирж:")
            for exchange, count in df['exchange'].value_counts().head(10).items():
                print(f"  {exchange:15} : {count:4} инструментов")
        
        # По валютам
        if 'currency' in df.columns and not df['currency'].isnull().all():
            print("\nПо валютам:")
            for currency, count in df['currency'].value_counts().head(10).items():
                print(f"  {currency:15} : {count:4} инструментов")
        
        # По class_code
        if 'class_code' in df.columns and not df['class_code'].isnull().all():
            print("\nТоп-10 class_code:")
            for class_code, count in df['class_code'].value_counts().head(10).items():
                print(f"  {class_code:15} : {count:4} инструментов")
        
        # Примеры инструментов
        print("\nПримеры инструментов (первые 15):")
        for i, (_, row) in enumerate(df.head(15).iterrows()):
            name_short = (row['name'][:35] + '...') if len(row['name']) > 35 else row['name']
            print(f"  {i+1:2}. {row['ticker']:12} - {name_short:38} ({row['type']}, {row['exchange']})")
        
        if len(df) > 15:
            print(f"  ... и еще {len(df) - 15} инструментов")
        
        print("="*70)

def main():
    """Точка входа"""
    print("🔍 СКРИПТ ПОЛУЧЕНИЯ ИНСТРУМЕНТОВ С country_of_risk = 'RU'")
    print("="*70)
    
    try:
        fetcher = InstrumentFetcherRU()
        result_file = fetcher.run()
        
        if result_file:
            print(f"\n✅ СКРИПТ УСПЕШНО ВЫПОЛНЕН!")
            print(f"📁 Файл с инструментами: {result_file}")
            print(f"📁 Расположение: корневая папка проекта")
            
            # Показываем команды для проверки
            filename = result_file.name
            print(f"\n📋 Размер файла: wc -l {filename}")
            print(f"📋 Структура: head -1 {filename} | tr ',' '\\n' | nl")
            print(f"📋 Просмотр: head -20 {filename}")
            
            print("\n🎯 Следующий шаг: использовать этот файл для загрузки исторических данных")
        else:
            print("\n❌ СКРИПТ ЗАВЕРШИЛСЯ С ОШИБКОЙ")
            print("   Проверьте .env файл и подключение к интернету")
            
    except KeyboardInterrupt:
        print("\n⏹️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
