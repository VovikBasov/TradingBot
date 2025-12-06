#!/usr/bin/env python3
"""
Тест Tinkoff API - запускать из корневой папки проекта
"""

import sys
import os

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_feed.tinkoff_client import TinkoffAPIClient

def main():
    print("🧪 Тестируем Tinkoff API...")
    
    try:
        client = TinkoffAPIClient()
        
        # Тестируем на SBER
        print("🔍 Проверяем стакан SBER...")
        client.print_pretty_orderbook("SBER")
        
        # Тестируем на GAZP
        print("\n🔍 Проверяем стакан GAZP...")
        client.print_pretty_orderbook("GAZP")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        print("ℹ️  Проверьте:")
        print("   - Токен в .env файле")
        print("   - Подключение к интернету")
        print("   - Правильность формата токена")

if __name__ == "__main__":
    main()
