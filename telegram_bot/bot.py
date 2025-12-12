#!/usr/bin/env python3
"""
Основной модуль Telegram бота
Запуск: python telegram_bot/bot.py
"""

import os
import sys
import asyncio
import signal
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
from telegram_bot.config import bot_state, TELEGRAM_CHAT_ID, send_notification
from src.utils.logger import log, log_business, log_command

# Загружаем переменные окружения
load_dotenv()

# Получаем конфигурацию
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Флаг для управления остановкой
shutdown_event = asyncio.Event()

async def send_startup_message(bot):
    """Отправляет сообщение о запуске бота"""
    if TELEGRAM_CHAT_ID and TELEGRAM_CHAT_ID != 'ваш_chat_id_сюда':
        message = "🤖 <b>Бот проснулся!</b>\n\nДля начала работы отправьте команду /start"
        await send_notification(bot, message)
        log.info("Сообщение о запуске отправлено")
        log_business("bot", "startup", "system")

async def send_shutdown_message(bot):
    """Отправляет сообщение об остановке бота"""
    if TELEGRAM_CHAT_ID and TELEGRAM_CHAT_ID != 'ваш_chat_id_сюда':
        message = "😴 <b>Бот ушёл спать</b>\n\nДля возобновления работы перезапустите бота"
        await send_notification(bot, message)
        log.info("Сообщение об остановке отправлено")
        log_business("bot", "shutdown", "system")

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    log.warning(f"Получен сигнал завершения {signum}")
    shutdown_event.set()

def create_application():
    """Создаёт и настраивает приложение бота"""
    # Создаём приложение с JobQueue
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    
    app.add_handler(CommandHandler("ticker", set_ticker))
    app.add_handler(CommandHandler("depth", set_depth))
    app.add_handler(CommandHandler("interval", set_interval))
    
    app.add_handler(CommandHandler("orderbook", get_orderbook))
    app.add_handler(CommandHandler("start_monitoring", start_monitoring))
    app.add_handler(CommandHandler("stop_monitoring", stop_monitoring))
    
    return app

async def main_async():
    """Асинхронная основная функция"""
    log.info("🤖 Бот запускается...")
    log_business("bot", "start", "system")
    
    if not TELEGRAM_BOT_TOKEN or "ваш_токен" in TELEGRAM_BOT_TOKEN:
        log.error("Токен бота не настроен!")
        return
    
    if not TELEGRAM_CHAT_ID or "ваш_chat_id" in TELEGRAM_CHAT_ID:
        log.warning("Chat ID не настроен!")
    
    try:
        # Создаём приложение
        application = create_application()
        
        # Инициализируем JobQueue вручную
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Устанавливаем флаг работы
        bot_state['is_running'] = True
        
        log.info("Бот инициализирован")
        log.info("JobQueue инициализирована")
        
        # Отправляем сообщение о запуске
        await send_startup_message(application.bot)
        
        log.info("📡 Бот запущен и работает... (Ctrl+C для остановки)")
        
        # Ждем сигнала завершения
        await shutdown_event.wait()
        
        log.info("Завершаем работу...")
        
        # Останавливаем бота
        await application.updater.stop()
        await application.stop()
        
        log.info("👋 Бот завершил работу")
        
    except KeyboardInterrupt:
        log.warning("Бот остановлен пользователем (Ctrl+C)")
        if 'application' in locals():
            await send_shutdown_message(application.bot)
            await application.updater.stop()
            await application.stop()
    except Exception as e:
        log.error(f"Ошибка запуска бота: {e}")
    finally:
        bot_state['is_running'] = False
        log_business("bot", "stop", "system")

def main():
    """Основная функция запуска бота"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Запускаем асинхронную основную функцию
        asyncio.run(main_async())
    except KeyboardInterrupt:
        log.info("Завершение работы...")
    except Exception as e:
        log.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
