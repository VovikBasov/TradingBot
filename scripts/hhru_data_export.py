#!/usr/bin/env python3
"""
Скрипт для выгрузки исторических данных HeadHunter (HHRU)
"""

import os
import sys
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

load_dotenv()

from tinkoff.invest import Client, CandleInterval
from tinkoff.invest.utils import now
from utils.logger import log

class HHDataExporter:
    def __init__(self):
        self.token = os.getenv('INVEST_TOKEN')
        if not self.token:
            log.error("❌ Токен не найден в .env файле")
            raise ValueError("Токен не найден")
        log.info("HeadHunter Data Exporter инициализирован")
    
    def find_hhru_instrument(self):
        """Находим инструмент HeadHunter по тикеру"""
        with Client(self.token) as client:
            # Пробуем разные варианты тикеров HeadHunter
            tickers_to_try = ["HHRU", "HHRS", "HH", "HHR"]
            
            for ticker in tickers_to_try:
                log.info(f"🔍 Ищем инструмент с тикером: {ticker}")
                instruments = client.instruments.find_instrument(query=ticker)
                
                for instrument in instruments.instruments:
                    if instrument.ticker.upper() == ticker.upper():
                        log.info(f"✅ Найден инструмент: {instrument.name} ({instrument.ticker})")
                        log.info(f"   FIGI: {instrument.figi}")
                        log.info(f"   Тип: {instrument.instrument_type}")
                        return instrument
            
            log.error("❌ Не удалось найти инструмент HeadHunter")
            return None
    
    def get_historical_candles(self, figi, from_date, to_date):
        """Получаем исторические свечи за период"""
        candles_data = []
        
        with Client(self.token) as client:
            # Получаем свечи по дням
            response = client.market_data.get_candles(
                figi=figi,
                from_=from_date,
                to=to_date,
                interval=CandleInterval.CANDLE_INTERVAL_DAY
            )
            
            for candle in response.candles:
                candles_data.append({
                    'time': candle.time.strftime('%Y-%m-%d %H:%M:%S'),
                    'open': self.quotation_to_float(candle.open),
                    'high': self.quotation_to_float(candle.high),
                    'low': self.quotation_to_float(candle.low),
                    'close': self.quotation_to_float(candle.close),
                    'volume': candle.volume,
                    'is_complete': candle.is_complete
                })
            
            log.info(f"📊 Получено {len(candles_data)} свечей")
            return candles_data
    
    def quotation_to_float(self, quotation):
        """Конвертируем Quotation в float"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def export_to_csv(self, candles_data, output_path):
        """Экспортируем данные в CSV"""
        if not candles_data:
            log.error("❌ Нет данных для экспорта")
            return False
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['time', 'open', 'high', 'low', 'close', 'volume', 'is_complete']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for candle in candles_data:
                    writer.writerow(candle)
            
            log.info(f"💾 Данные сохранены в: {output_path}")
            return True
            
        except Exception as e:
            log.error(f"❌ Ошибка при сохранении CSV: {e}")
            return False
    
    def run_export(self):
        """Основная функция экспорта"""
        log.info("🚀 Запускаем экспорт данных HeadHunter...")
        
        # Находим инструмент
        instrument = self.find_hhru_instrument()
        if not instrument:
            return False
        
        # Период данных
        from_date = datetime(2024, 1, 1)
        to_date = datetime(2025, 11, 16)
        
        log.info(f"📅 Период данных: {from_date.strftime('%d.%m.%Y')} - {to_date.strftime('%d.%m.%Y')}")
        
        # Получаем исторические данные
        candles_data = self.get_historical_candles(
            instrument.figi, 
            from_date, 
            to_date
        )
        
        if not candles_data:
            log.error("❌ Не удалось получить исторические данные")
            return False
        
        # Сохраняем на рабочий стол
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_filename = f"headhunter_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = os.path.join(desktop_path, output_filename)
        
        success = self.export_to_csv(candles_data, output_path)
        
        if success:
            log.info("✅ Экспорт завершен успешно!")
            print(f"\n📁 Файл сохранен: {output_path}")
            print(f"📊 Количество записей: {len(candles_data)}")
        
        return success

def main():
    """Точка входа"""
    try:
        exporter = HHDataExporter()
        exporter.run_export()
        
    except Exception as e:
        log.error(f"❌ Критическая ошибка: {e}")
        print("\n💡 Возможные решения:")
        print("   - Проверьте токен в .env файле")
        print("   - Убедитесь что торги по HHRU идут")
        print("   - Проверьте подключение к интернету")

if __name__ == "__main__":
    main()
