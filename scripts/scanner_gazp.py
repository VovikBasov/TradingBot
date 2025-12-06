#!/usr/bin/env python3
"""
Скринер стакана по Газпрому
Запуск: python scripts/scanner_gazp.py
"""

import sys
import os
import time

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_feed.orderbook import MOEXOrderbook
from utils.logger import log

def main():
    """Основная функция скринера"""
    log.info("🚀 Запускаем скринер стакана...")
    
    client = MOEXOrderbook()
    
    # Сначала тестируем на SBER (он всегда торгуется)
    log.info("Тестируем подключение на SBER...")
    test_orderbook = client.get_orderbook("SBER")
    if test_orderbook and ('bids' in test_orderbook or 'asks' in test_orderbook):
        log.info("✅ Подключение к MOEX работает")
    else:
        log.error("❌ Проблема с подключением к MOEX")
        return
    
    try:
        while True:
            # Очищаем консоль
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("🎯 СКРИНЕР СТАКАНА - ГАЗПРОМ (GAZP)")
            print("Для остановки нажмите Ctrl+C\n")
            
            # Получаем и выводим стакан
            client.print_pretty_orderbook("GAZP")
            
            # Ждём 5 секунд до следующего обновления
            print("\n🔄 Обновление через 5 секунд...")
            time.sleep(5)
            
    except KeyboardInterrupt:
        log.info("⏹️  Скринер остановлен пользователем")
    except Exception as e:
        log.error(f"❌ Ошибка в скринере: {e}")

if __name__ == "__main__":
    main()
