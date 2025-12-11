#!/usr/bin/env python3
"""
Получение Chat ID для Telegram бота
Запуск: python telegram_bot/get_chat_id.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Добавляем корень проекта в путь Python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

async def get_chat_id():
    # Загружаем переменные из .env
    load_dotenv()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ Токен не найден в .env файле")
        print("   Добавьте TELEGRAM_BOT_TOKEN=ваш_токен в .env")
        return False
    
    if "ваш_токен_бота_сюда" in token or "your_bot_token_here" in token:
        print("❌ Токен не изменен!")
        print("   Замените значение TELEGRAM_BOT_TOKEN в .env на реальный токен")
        return False
    
    print("🔍 ПОЛУЧЕНИЕ TELEGRAM CHAT ID")
    
    try:
        bot = Bot(token=token)
        print("🔄 Проверяем подключение к боту...")
        bot_info = await bot.get_me()
        print(f"✅ Бот: @{bot_info.username}")
        
        print("📩 Ищем последние сообщения...")
        updates = await bot.get_updates(timeout=10, limit=10)
        
        if not updates:
            print("❌ Сообщений не найдено!")
            print("📱 Что делать:")
            print("   1. Откройте Телеграм")
            print(f"   2. Найдите бота: @{bot_info.username}")
            print("   3. Нажмите START или напишите любое сообщение")
            print("   4. Запустите этот скрипт снова")
            return False
        
        print(f"✅ Найдено сообщений: {len(updates)}")
        
        # Используем последний чат
        last_update = updates[-1]
        if last_update.message:
            chat_id = last_update.message.chat.id
        elif last_update.callback_query:
            chat_id = last_update.callback_query.message.chat.id
        else:
            print("❌ Не удалось извлечь chat_id")
            return False
        
        print(f"🎯 ПОСЛЕДНИЙ ЧАТ ID: {chat_id}")
        
        # Обновляем .env файл
        env_path = project_root / ".env"
        if env_path.exists():
            with open(env_path, "r") as f:
                lines = f.readlines()
            
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith("TELEGRAM_CHAT_ID="):
                    lines[i] = f"TELEGRAM_CHAT_ID={chat_id}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"\nTELEGRAM_CHAT_ID={chat_id}\n")
            
            with open(env_path, "w") as f:
                f.writelines(lines)
            
            print(f"✅ Chat ID сохранен в .env файл")
        else:
            print(f"📝 Создайте .env и добавьте строку:")
            print(f"TELEGRAM_CHAT_ID={chat_id}")
        
        return True
        
    except TelegramError as e:
        print(f"❌ Ошибка Telegram API: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def main():
    print("🚀 Запуск получения Chat ID для Telegram бота")
    
    # Проверяем виртуальное окружение
    if sys.prefix == sys.base_prefix:
        print("⚠️  Совет: Активируйте виртуальное окружение: source trading_env/bin/activate")
    
    success = asyncio.run(get_chat_id())
    
    if success:
        print("🎉 Готово! Chat ID получен и сохранен.")
    else:
        print("❌ Не удалось получить Chat ID")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
