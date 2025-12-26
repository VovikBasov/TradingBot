#!/usr/bin/env python3
"""
Тестовый скрипт для проверки сканера
"""

import asyncio
import os
import sys

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения из .env файла
from dotenv import load_dotenv
load_dotenv()

async def test_scanner():
    """Тестовая функция"""
    from supertrend_scanner import SupertrendScanner
    
    try:
        scanner = SupertrendScanner()
    except ValueError as e:
        print(f"❌ Ошибка: {e}")
        print("Убедитесь, что в .env файле указана переменная INVEST_TOKEN")
        return
    
    print("Тест сканера Supertrend...")
    print("Параметры стратегии:")
    print(f"  - ATR период: {scanner.atr_period}")
    print(f"  - Supertrend множитель: {scanner.supertrend_factor}")
    print(f"  - RSI период: {scanner.rsi_period}")
    print(f"  - Стоп-лосс: {scanner.stop_loss_perc}%")
    print(f"  - Тейк-профит: {scanner.take_profit_perc}%")
    print("="*50)
    
    await scanner.scan_once()

if __name__ == "__main__":
    asyncio.run(test_scanner())
