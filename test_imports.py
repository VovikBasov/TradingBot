#!/usr/bin/env python3
"""
Тест импортов всех модулей бота
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь Python
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🔍 Проверяем импорты модулей бота...")

try:
    from telegram_bot.config import bot_state, TELEGRAM_BOT_TOKEN
    print("✅ config.py")
except Exception as e:
    print(f"❌ config.py: {e}")

try:
    from telegram_bot.handlers.basic import start, help_command, status
    print("✅ handlers.basic")
except Exception as e:
    print(f"❌ handlers.basic: {e}")

try:
    from telegram_bot.handlers.settings import set_ticker, set_depth, set_interval
    print("✅ handlers.settings")
except Exception as e:
    print(f"❌ handlers.settings: {e}")

try:
    from telegram_bot.handlers.orderbook import get_orderbook, start_monitoring, stop_monitoring
    print("✅ handlers.orderbook")
except Exception as e:
    print(f"❌ handlers.orderbook: {e}")

try:
    from telegram_bot.services.orderbook_service import get_orderbook as get_orderbook_data
    print("✅ services.orderbook_service")
except Exception as e:
    print(f"❌ services.orderbook_service: {e}")

print("\n🎯 Проверка импортов завершена!")
