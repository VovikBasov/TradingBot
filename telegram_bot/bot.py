#!/usr/bin/env python3
"""
Основной модуль Telegram бота для получения стаканов
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь Python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if __name__ == "__main__":
    print("🤖 Telegram Bot для торгового бота")
    print("=" * 50)
    
    if not TELEGRAM_BOT_TOKEN or "ваш_токен" in TELEGRAM_BOT_TOKEN:
        print("❌ Токен бота не настроен!")
        print("   Запустите: python telegram_bot/get_chat_id.py")
    else:
        print("✅ Токен бота найден")
        
    if not TELEGRAM_CHAT_ID or "ваш_chat_id" in TELEGRAM_CHAT_ID:
        print("❌ Chat ID не настроен!")
        print("   Запустите: python telegram_bot/get_chat_id.py")
    else:
        print(f"✅ Chat ID найден: {TELEGRAM_CHAT_ID}")
