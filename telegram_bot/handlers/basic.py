#!/usr/bin/env python3
"""
Обработчики базовых команд бота
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.config import bot_state

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🤖 <b>Торговый бот для получения стакана</b>

Я помогаю получать стакан заявок с биржи через Telegram.

<b>Основные команды:</b>
/ticker <тикер> - установить тикер (например: /ticker SBER)
/depth <число> - установить глубину стакана (например: /depth 10)
/interval <секунды> - установить интервал отправки (например: /interval 5)

<b>Команды стакана:</b>
/orderbook - получить текущий стакан
/start_monitoring - запустить периодическую отправку
/stop_monitoring - остановить отправку

<b>Другие команды:</b>
/status - текущие настройки
/help - помощь

<b>Пример настройки:</b>
/ticker SBER
/depth 5
/interval 10
/start_monitoring
"""
    await update.message.reply_text(welcome_text, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📚 <b>Справка по командам</b>

<b>Настройки:</b>
• /ticker <тикер> - Установить тикер бумаги (пример: SBER, GAZP, YNDX)
• /depth <число> - Глубина стакана (от 1 до 50)
• /interval <секунды> - Интервал отправки (от 1 до 3600)

<b>Стакан:</b>
• /orderbook - Получить текущий стакан
• /start_monitoring - Запустить периодическую отправку
• /stop_monitoring - Остановить отправку

<b>Информация:</b>
• /status - Текущие настройки
• /help - Эта справка

<b>Примеры использования:</b>
1. Настройка: /ticker SBER → /depth 10 → /interval 30
2. Тест: /orderbook
3. Запуск мониторинга: /start_monitoring
4. Остановка: /stop_monitoring
"""
    await update.message.reply_text(help_text, parse_mode='HTML')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    ticker = bot_state.get('ticker', 'SBER')
    depth = bot_state.get('depth', 5)
    interval = bot_state.get('interval', 10)
    monitoring = "✅ Запущен" if bot_state.get('monitoring_job') else "❌ Остановлен"
    
    status_text = f"""
📊 <b>Текущие настройки:</b>

📈 <b>Тикер:</b> {ticker}
📏 <b>Глубина стакана:</b> {depth}
⏰ <b>Интервал отправки:</b> {interval} секунд
🔄 <b>Мониторинг:</b> {monitoring}

<b>Используйте:</b>
/orderbook - получить стакан сейчас
/start_monitoring - запустить периодическую отправку
/help - список всех команд
"""
    await update.message.reply_text(status_text, parse_mode='HTML')
