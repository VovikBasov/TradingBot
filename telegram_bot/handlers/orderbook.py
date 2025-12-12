#!/usr/bin/env python3
"""
Обработчики команд для работы со стаканом (упрощенная версия)
"""

import asyncio
from telegram import Update
from telegram.ext import ContextTypes, JobQueue
from telegram_bot.config import bot_state
from telegram_bot.services.orderbook_service import get_orderbook as get_orderbook_data, format_orderbook_message

async def get_orderbook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /orderbook"""
    try:
        ticker = bot_state.get('ticker', 'SBER')
        depth = bot_state.get('depth', 5)
        await update.message.reply_text(f"🔍 Получаю стакан {ticker}...")
        orderbook_data = await get_orderbook_data(ticker, depth)
        if not orderbook_data:
            await update.message.reply_text(f"❌ Не удалось получить стакан для {ticker}.")
            return
        message = await format_orderbook_message(orderbook_data)
        await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")

async def send_orderbook_job(context: ContextTypes.DEFAULT_TYPE):
    """Задача для периодической отправки стакана"""
    try:
        ticker = bot_state.get('ticker', 'SBER')
        depth = bot_state.get('depth', 5)
        orderbook_data = await get_orderbook_data(ticker, depth)
        if not orderbook_data:
            print(f"❌ Не удалось получить стакан для {ticker} в задаче мониторинга")
            return
        message = await format_orderbook_message(orderbook_data)
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=message,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"❌ Ошибка в задаче мониторинга: {e}")

async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start_monitoring"""
    try:
        if bot_state.get('monitoring_job'):
            await update.message.reply_text("⚠️ Мониторинг уже запущен!")
            return
        ticker = bot_state.get('ticker', 'SBER')
        depth = bot_state.get('depth', 5)
        interval = bot_state.get('interval', 10)
        if interval < 1:
            await update.message.reply_text("❌ Интервал должен быть не менее 1 секунды")
            return
        job_queue = context.job_queue
        if job_queue is None:
            await update.message.reply_text("❌ Ошибка: JobQueue не инициализирован")
            return
        job = job_queue.run_repeating(
            send_orderbook_job,
            interval=interval,
            first=1,
            chat_id=update.effective_chat.id,
            name=f"orderbook_monitoring_{ticker}"
        )
        bot_state['monitoring_job'] = job
        await update.message.reply_text(
            f"✅ Мониторинг запущен!\n\n"
            f"📊 <b>Тикер:</b> {ticker}\n"
            f"📏 <b>Глубина:</b> {depth}\n"
            f"⏰ <b>Интервал:</b> {interval} сек\n\n"
            f"Для остановки: /stop_monitoring",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка запуска мониторинга: {str(e)[:100]}")

async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stop_monitoring"""
    try:
        job = bot_state.get('monitoring_job')
        if job:
            job.schedule_removal()
            bot_state['monitoring_job'] = None
            await update.message.reply_text("✅ Мониторинг остановлен!")
        else:
            await update.message.reply_text("⚠️ Мониторинг не был запущен")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка остановки мониторинга: {str(e)[:100]}")
