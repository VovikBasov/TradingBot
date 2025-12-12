#!/usr/bin/env python3
"""
Обработчики команд для работы со стаканом (упрощенная версия)
"""

import asyncio
from telegram import Update
from telegram.ext import ContextTypes, JobQueue
from telegram_bot.config import bot_state
from telegram_bot.services.orderbook_service import get_orderbook as get_orderbook_data, format_orderbook_message

async def send_orderbook_job(context: ContextTypes.DEFAULT_TYPE):
    """Задача для периодической отправки стакана"""
    try:
        ticker = bot_state.get('ticker', 'SBER')
        depth = bot_state.get('depth', 5)
        print(f"🔄 [Задача мониторинга] Получаем стакан {ticker}...")
        
        orderbook_data = await get_orderbook_data(ticker, depth)
        if not orderbook_data:
            print(f"❌ [Задача мониторинга] Не удалось получить стакан для {ticker}")
            return
        
        message = await format_orderbook_message(orderbook_data)
        
        # Добавляем заголовок мониторинга
        message = f"📡 <b>АВТОМАТИЧЕСКИЙ МОНИТОРИНГ</b>\n" + message
        
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=message,
            parse_mode='HTML'
        )
        
        print(f"✅ [Задача мониторинга] Стакан {ticker} отправлен")
        
    except Exception as e:
        print(f"❌ [Задача мониторинга] Ошибка: {e}")

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

async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start_monitoring"""
    try:
        # Проверяем, не запущен ли уже мониторинг
        if bot_state.get('monitoring_job'):
            await update.message.reply_text("⚠️ Мониторинг уже запущен!")
            return
        
        # Получаем настройки
        ticker = bot_state.get('ticker', 'SBER')
        depth = bot_state.get('depth', 5)
        interval = bot_state.get('interval', 10)
        
        if interval < 1:
            await update.message.reply_text("❌ Интервал должен быть не менее 1 секунды")
            return
        
        # Получаем job_queue из контекста приложения
        job_queue = context.application.job_queue
        
        if job_queue is None:
            # Если job_queue не инициализирована, создаем новую
            job_queue = JobQueue()
            job_queue.set_application(context.application)
            await job_queue.start()
        
        # Создаем задачу мониторинга
        job = job_queue.run_repeating(
            send_orderbook_job,
            interval=interval,
            first=3,  # Первый запуск через 3 секунды
            chat_id=update.effective_chat.id,
            name=f"orderbook_monitoring_{ticker}"
        )
        
        # Сохраняем задачу в состоянии бота
        bot_state['monitoring_job'] = job
        
        # Сохраняем job_queue в состоянии для последующего использования
        bot_state['job_queue'] = job_queue
        
        await update.message.reply_text(
            f"✅ Мониторинг запущен!\n\n"
            f"📊 <b>Тикер:</b> {ticker}\n"
            f"📏 <b>Глубина:</b> {depth}\n"
            f"⏰ <b>Интервал:</b> {interval} секунд\n\n"
            f"<i>Первое обновление через 3 секунды...</i>\n\n"
            f"Для остановки: /stop_monitoring",
            parse_mode='HTML'
        )
        
        print(f"🚀 Мониторинг запущен: {ticker}, интервал {interval}с")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка запуска мониторинга: {str(e)[:100]}")
        import traceback
        print(f"Ошибка запуска мониторинга: {traceback.format_exc()}")

async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stop_monitoring"""
    try:
        job = bot_state.get('monitoring_job')
        
        if job:
            # Удаляем задачу
            job.schedule_removal()
            bot_state['monitoring_job'] = None
            
            # Останавливаем job_queue если она пустая
            if bot_state.get('job_queue'):
                jobs = bot_state['job_queue'].jobs
                if not jobs:
                    await bot_state['job_queue'].stop()
                    bot_state['job_queue'] = None
            
            await update.message.reply_text("✅ Мониторинг остановлен!")
            print("⏹️ Мониторинг остановлен")
        else:
            await update.message.reply_text("⚠️ Мониторинг не был запущен")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка остановки мониторинга: {str(e)[:100]}")
