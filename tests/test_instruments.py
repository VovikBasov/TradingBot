#!/usr/bin/env python3
"""
Тест поиска инструментов
"""

import os
import sys
from dotenv import load_dotenv

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

load_dotenv()

def main():
    print("🧪 Тестируем поиск инструментов...")
    
    token = os.getenv('INVEST_TOKEN')
    if not token:
        print("❌ Токен не найден")
        return
    
    try:
        from tinkoff.invest import Client
        from tinkoff.invest.schemas import InstrumentStatus
        
        with Client(token) as client:
            # Тестируем поиск SBER
            instruments = client.instruments.find_instrument(query="SBER")
            print(f"🔍 Найдено инструментов по SBER: {len(instruments.instruments)}")
            
            for i, instrument in enumerate(instruments.instruments[:3]):  # Покажем первые 3
                print(f"\nИнструмент {i+1}:")
                print(f"  Тикер: {instrument.ticker}")
                print(f"  Название: {instrument.name}")
                print(f"  FIGI: {instrument.figi}")
                print(f"  State: {instrument.state}")
                print(f"  Status: {InstrumentStatus(instrument.state).name}")
                
                # Покажем все атрибуты объекта
                print(f"  Все атрибуты: {[attr for attr in dir(instrument) if not attr.startswith('_')]}")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
