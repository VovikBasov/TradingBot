#!/usr/bin/env python3
"""
Сервис для получения стакана через Tinkoff API
"""

import asyncio
from typing import Optional, Dict, Any
from telegram_bot.services.tinkoff_service import get_tinkoff_service

async def get_orderbook(ticker: str, depth: int = 5) -> Optional[Dict[str, Any]]:
    """
    Получает стакан по тикеру через Tinkoff API
    
    Args:
        ticker: Тикер инструмента (например, 'SBER')
        depth: Глубина стакана
        
    Returns:
        Словарь с данными стакана или None при ошибке
    """
    try:
        # Получаем сервис
        service = await get_tinkoff_service()
        
        # Получаем стакан
        orderbook_data = await service.get_orderbook(ticker, depth)
        
        return orderbook_data
        
    except Exception as e:
        print(f"❌ Ошибка в get_orderbook: {e}")
        return None

async def format_orderbook_message(data: Dict[str, Any]) -> str:
    """
    Форматирует данные стакана для отправки в Telegram
    
    Args:
        data: Данные стакана
        
    Returns:
        Отформатированное сообщение
    """
    if not data:
        return "❌ Не удалось получить данные стакана. Проверьте тикер и подключение к интернету."
    
    try:
        service = await get_tinkoff_service()
        return service.format_orderbook_for_telegram(data)
    except Exception as e:
        print(f"❌ Ошибка форматирования: {e}")
        return "❌ Ошибка при форматировании данных стакана."
