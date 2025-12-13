#!/usr/bin/env python3
"""
Тест исправления импортов и работы TinkoffService
"""

import sys
import asyncio
from pathlib import Path

# Обновляем путь для импорта после перемещения в tests/
project_root = Path(__file__).parent.parent  # Поднимаемся на 2 уровня выше
sys.path.insert(0, str(project_root))

async def test():
    """Тестируем получение стакана через TinkoffService"""
    from telegram_bot.services.tinkoff_service import TinkoffService
    
    svc = TinkoffService()
    print("🧪 Тестируем получение стакана для SBER...")
    data = await svc.get_orderbook("SBER", 2)
    
    if data:
        print(f"✅ Успех! Получено {len(data['bids'])} бидов и {len(data['asks'])} асков.")
        print(f"   Лучшая покупка: {data['best_bid']}, Лучшая продажа: {data['best_ask']}")
    else:
        print("❌ Не удалось получить данные")

def main():
    """Основная функция"""
    print("🚀 Запуск теста исправления импортов...")
    print("=" * 50)
    
    asyncio.run(test())
    
    print("\n✅ Тест завершён!")

if __name__ == "__main__":
    main()
