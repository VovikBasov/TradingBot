#!/usr/bin/env python3
"""
Простой тест стакана - запускать из корневой папки проекта
"""

import sys
import os

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_feed.orderbook import MOEXOrderbook

def main():
    print("🧪 Тестируем стакан...")
    
    client = MOEXOrderbook()
    
    # Тестируем на SBER (он всегда торгуется)
    print("🔍 Проверяем стакан SBER...")
    client.print_pretty_orderbook("SBER")
    
    # Тестируем на GAZP
    print("\n🔍 Проверяем стакан GAZP...")
    client.print_pretty_orderbook("GAZP")

if __name__ == "__main__":
    main()
