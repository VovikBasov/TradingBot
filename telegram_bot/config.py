#!/usr/bin/env python3
"""
Конфигурация и состояние бота
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройки бота из .env
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'ваш_токен_бота_сюда')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'ваш_chat_id_сюда')

# Настройки Tinkoff из .env
INVEST_TOKEN = os.getenv('INVEST_TOKEN', 'ваш_токен_сюда')
SANDBOX = os.getenv('SANDBOX', 'true').lower() == 'true'

# Состояние бота (хранится в памяти)
bot_state = {
    'ticker': os.getenv('DEFAULT_TICKER', 'SBER'),
    'depth': int(os.getenv('DEFAULT_DEPTH', 5)),
    'interval': int(os.getenv('DEFAULT_INTERVAL', 10)),
    'monitoring_job': None,  # Задача мониторинга
    'job_queue': None,       # JobQueue для планирования задач
    'is_running': False      # Флаг работы бота
}

async def send_notification(bot, message: str):
    """Отправляет уведомление в чат"""
    if TELEGRAM_CHAT_ID and TELEGRAM_CHAT_ID != 'ваш_chat_id_сюда':
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='HTML'
            )
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления: {e}")
            return False
    return False
