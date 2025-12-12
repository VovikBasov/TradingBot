#!/usr/bin/env python3
"""
Основной модуль Telegram бота
Запуск: python telegram_bot/bot.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Добавляем корень проекта в путь Python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Импортируем обработчики
from telegram_bot.handlers.basic import start, help_command, status
from telegram_bot.handlers.settings import set_ticker, set_depth, set_interval
from telegram_bot.handlers.orderbook import get_orderbook, start_monitoring, stop_monitoring

# Загружаем переменные окружения
load_dotenv()

# Получаем конфигурацию
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def create_application():
    """Создаёт и настраивает приложение бота"""
    # Создаём приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    
    application.add_handler(CommandHandler("ticker", set_ticker))
    application.add_handler(CommandHandler("depth", set_depth))
    application.add_handler(CommandHandler("interval", set_interval))
    
    application.add_handler(CommandHandler("orderbook", get_orderbook))
    application.add_handler(CommandHandler("start_monitoring", start_monitoring))
    application.add_handler(CommandHandler("stop_monitoring", stop_monitoring))
    
    return application

def main():
    """Основная функция запуска бота"""
    print("🤖 Бот запускается...")
    
    if not TELEGRAM_BOT_TOKEN or "ваш_токен" in TELEGRAM_BOT_TOKEN:
        print("❌ Токен бота не настроен!")
        print("   Проверьте TELEGRAM_BOT_TOKEN в .env файле")
        return
    
    try:
        # Создаём приложение
        application = create_application()
        
        # Запускаем бота с правильным методом для версии 22.5
        print("✅ Бот инициализирован")
        print("📡 Запускаем polling... (Ctrl+C для остановки)")
        
        # Для python-telegram-bot 22.5 используем run_polling
        application.run_polling()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
