#!/usr/bin/env python3
"""
Тест мониторинга стакана
"""

import sys
import os
from pathlib import Path
import asyncio

# Обновляем путь для импорта после перемещения в tests/
project_root = Path(__file__).parent.parent  # Поднимаемся на 2 уровня выше
sys.path.insert(0, str(project_root))

async def test_monitoring():
    """Тестируем получение стакана"""
    print("🧪 Тестируем получение стакана для мониторинга...")
    
    try:
        from telegram_bot.services.tinkoff_service import TinkoffService
        service = TinkoffService()
        
        # Тестируем получение стакана
        ticker = "SBER"
        depth = 5
        
        print(f"🔍 Получаем стакан для {ticker}...")
        data = await service.get_orderbook(ticker, depth)
        
        if data:
            print(f"✅ Стакан получен!")
            print(f"   Тикер: {data['ticker']}")
            print(f"   Название: {data['name']}")
            print(f"   Аски: {len(data['asks'])} записей")
            print(f"   Биды: {len(data['bids'])} записей")
            
            # Показываем форматированное сообщение
            message = service.format_orderbook_for_telegram(data)
            print("\n📨 Форматированное сообщение для Telegram:")
            print("-" * 50)
            print(message)
            print("-" * 50)
            
            return True
        else:
            print("❌ Не удалось получить стакан")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка теста: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция"""
    print("🚀 Тест мониторинга стакана")
    print("=" * 50)
    
    # Проверяем наличие токена
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('INVEST_TOKEN')
    if not token or "ваш_токен" in token:
        print("❌ Токен Tinkoff не настроен!")
        print("   Проверьте файл .env")
        return
    
    # Запускаем тест
    success = asyncio.run(test_monitoring())
    
    if success:
        print("\n✅ Тест пройден! Мониторинг должен работать")
    else:
        print("\n❌ Тест не пройден. Проверьте настройки Tinkoff API")

if __name__ == "__main__":
    main()
