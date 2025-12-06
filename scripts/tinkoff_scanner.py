#!/usr/bin/env python3
"""
Скринер стаканов на Tinkoff API (боевой контур)
"""

import sys
import os
import time
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_feed.tinkoff_client_simple import TinkoffAPIClientSimple
from utils.logger import log

def main():
    """Основная функция скринера"""
    log.info("🚀 Запускаем скринер на Tinkoff API (БОЕВОЙ КОНТУР)...")
    
    try:
        client = TinkoffAPIClientSimple()
        
        # Тестируем подключение
        test_data = client.get_orderbook("SBER")
        if test_data:
            log.info("✅ Подключение к Tinkoff API работает")
        else:
            log.error("❌ Проблема с подключением к Tinkoff API")
            return
    
    except Exception as e:
        log.error(f"❌ Ошибка инициализации: {e}")
        return
    
    # Список тикеров для мониторинга
    tickers = ["ABIO"]
    
    try:
        while True:
            # Очищаем консоль
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("🎯 СКРИНЕР СТАКАНОВ - TINKOFF API (БОЕВОЙ КОНТУР)")
            print("ДАННЫЕ РЕАЛЬНЫЕ - БУДЬТЕ ОСТОРОЖНЫ!")
            print("Для остановки нажмите Ctrl+C\n")
            
            for ticker in tickers:
                client.print_pretty_orderbook(ticker, depth=3)
                print()
            
            print("🔄 Обновление через 1 секунд...")
            time.sleep(1)
            
    except KeyboardInterrupt:
        log.info("⏹️  Скринер остановлен пользователем")
    except Exception as e:
        log.error(f"❌ Ошибка в скринере: {e}")

if __name__ == "__main__":
    main()
