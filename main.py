#!/usr/bin/env python3
"""
Главный файл trading бота
"""

import sys
import os

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.logger import log
from data_feed.moex_client import MOEXClient

def main():
    """Основная функция"""
    log.info("🚀 Запускаем trading бот...")
    
    # Тестируем компоненты
    client = MOEXClient()
    
    # Получаем данные по SBER
    sber_info = client.get_security_info("SBER")
    if sber_info:
        log.info("✅ MOEX API работает")
    
    log.info("🎯 Trading бот готов к работе!")

if __name__ == "__main__":
    main()
