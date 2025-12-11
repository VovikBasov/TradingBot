#!/usr/bin/env python3
"""
Обработчики команд настройки
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.config import bot_state

async def set_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /ticker"""
    if not context.args:
        await update.message.reply_text("❌ Укажите тикер. Пример: /ticker SBER")
        return
    
    ticker = context.args[0].upper().strip()
    
    # Простая валидация тикера
    if not ticker.isalpha():
        await update.message.reply_text("❌ Тикер должен содержать только буквы")
        return
    
    if len(ticker) > 10:
        await update.message.reply_text("❌ Тикер слишком длинный")
        return
    
    # Сохраняем в состоянии
    bot_state['ticker'] = ticker
    
    await update.message.reply_text(f"✅ Тикер установлен: <b>{ticker}</b>\n\nИспользуйте /orderbook для проверки", parse_mode='HTML')

async def set_depth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /depth"""
    if not context.args:
        await update.message.reply_text("❌ Укажите глубину. Пример: /depth 10")
        return
    
    try:
        depth = int(context.args[0])
        
        if depth < 1 or depth > 50:
            await update.message.reply_text("❌ Глубина должна быть от 1 до 50")
            return
        
        # Сохраняем в состоянии
        bot_state['depth'] = depth
        
        await update.message.reply_text(f"✅ Глубина стакана установлена: <b>{depth}</b>", parse_mode='HTML')
        
    except ValueError:
        await update.message.reply_text("❌ Глубина должна быть числом")

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /interval"""
    if not context.args:
        await update.message.reply_text("❌ Укажите интервал. Пример: /interval 10")
        return
    
    try:
        interval = int(context.args[0])
        
        if interval < 1:
            await update.message.reply_text("❌ Интервал должен быть не менее 1 секунды")
            return
        
        if interval > 3600:
            await update.message.reply_text("❌ Интервал должен быть не более 3600 секунд (1 час)")
            return
        
        # Сохраняем в состоянии
        bot_state['interval'] = interval
        
        # Если мониторинг запущен, нужно перезапустить его с новым интервалом
        job = bot_state.get('monitoring_job')
        if job:
            job.schedule_removal()
            bot_state['monitoring_job'] = None
            await update.message.reply_text(
                f"✅ Интервал установлен: <b>{interval}</b> секунд\n\n"
                f"⚠️ Мониторинг был остановлен. Запустите снова: /start_monitoring",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(f"✅ Интервал установлен: <b>{interval}</b> секунд", parse_mode='HTML')
        
    except ValueError:
        await update.message.reply_text("❌ Интервал должен быть числом")
