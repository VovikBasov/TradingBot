#!/usr/bin/env python3
"""
Сервис для работы с Tinkoff API (асинхронный)
Использует gRPC для получения стаканов
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import sys

# Добавляем корень проекта в путь Python
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

try:
    from tinkoff.invest import AsyncClient
    from tinkoff.invest.schemas import InstrumentStatus, InstrumentIdType
    print("✅ Tinkoff библиотеки импортированы")
except ImportError as e:
    print(f"❌ Ошибка импорта Tinkoff: {e}")
    raise

class TinkoffService:
    """Сервис для работы с Tinkoff Invest API"""
    
    def __init__(self):
        self.token = os.getenv('INVEST_TOKEN')
        if not self.token:
            raise ValueError("❌ Токен Tinkoff API не найден в .env файле")
        
        self._client = None
        print("🚀 TinkoffService инициализирован")
    
    async def __aenter__(self):
        """Контекстный менеджер"""
        self._client = AsyncClient(self.token)
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Завершение работы"""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def find_instrument_by_ticker(self, ticker: str):
        """Находит инструмент по тикеру"""
        try:
            # Сначала получаем все акции
            shares_response = await self._client.instruments.shares()
            
            # Ищем по точному тикеру
            for instrument in shares_response.instruments:
                if (instrument.ticker == ticker and 
                    instrument.exchange == 'MOEX' and
                    instrument.class_code == 'TQBR'):
                    print(f"✅ Найдена акция: {instrument.name} ({instrument.ticker})")
                    return instrument
            
            print(f"❌ Акция с тикером '{ticker}' не найдена на MOEX")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка поиска инструмента '{ticker}': {e}")
            return None
    
    async def get_orderbook(self, ticker: str, depth: int = 5) -> Optional[Dict[str, Any]]:
        """
        Получает стакан по тикеру
        
        Returns:
            Словарь с данными стакана или None при ошибке
        """
        try:
            instrument = await self.find_instrument_by_ticker(ticker)
            if not instrument:
                return None
            
            # Получаем стакан
            orderbook = await self._client.market_data.get_order_book(
                figi=instrument.figi,
                depth=depth
            )
            
            # Форматируем результат
            result = {
                'ticker': ticker,
                'name': instrument.name,
                'asks': [],
                'bids': [],
                'best_bid': None,
                'best_ask': None,
                'timestamp': datetime.now()
            }
            
            # Обрабатываем аски (продажа)
            if orderbook.asks:
                result['best_ask'] = self._quotation_to_float(orderbook.best_ask_price)
                for ask in orderbook.asks[:depth]:
                    price = self._quotation_to_float(ask.price)
                    quantity = ask.quantity
                    result['asks'].append({
                        'price': price,
                        'quantity': quantity
                    })
            
            # Обрабатываем биды (покупка)
            if orderbook.bids:
                result['best_bid'] = self._quotation_to_float(orderbook.best_bid_price)
                for bid in orderbook.bids[:depth]:
                    price = self._quotation_to_float(bid.price)
                    quantity = bid.quantity
                    result['bids'].append({
                        'price': price,
                        'quantity': quantity
                    })
            
            return result
            
        except Exception as e:
            print(f"❌ Ошибка получения стакана '{ticker}': {e}")
            return None
    
    def _quotation_to_float(self, quotation) -> float:
        """Конвертирует Quotation в float"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def format_orderbook_for_telegram(self, data: Dict[str, Any]) -> str:
        """Форматирует стакан для отправки в Telegram"""
        if not data:
            return "❌ Не удалось получить данные стакана"
        
        # Создаём заголовок
        timestamp = data['timestamp'].strftime('%H:%M:%S')
        message = f"📊 <b>СТАКАН {data['ticker']}</b>\n"
        message += f"<i>{data['name']}</i>\n\n"
        
        # Продажа (asks)
        if data['asks']:
            message += "💰 <b>ПРОДАЖА:</b>\n"
            for ask in data['asks'][:5]:  # Только первые 5 уровней
                message += f"  {ask['price']:>8.2f} | {ask['quantity']:>6} лотов\n"
        else:
            message += "💰 <b>ПРОДАЖА:</b> нет данных\n"
        
        message += "\n"
        
        # Покупка (bids)
        if data['bids']:
            message += "🛒 <b>ПОКУПКА:</b>\n"
            for bid in data['bids'][:5]:
                message += f"  {bid['price']:>8.2f} | {bid['quantity']:>6} лотов\n"
        else:
            message += "🛒 <b>ПОКУПКА:</b> нет данных\n"
        
        message += "\n"
        
        # Спред и время
        if data['best_bid'] and data['best_ask']:
            spread = data['best_ask'] - data['best_bid']
            spread_percent = (spread / data['best_bid']) * 100
            message += f"💎 <b>Спрос:</b> {data['best_bid']:.2f}\n"
            message += f"💎 <b>Предложение:</b> {data['best_ask']:.2f}\n"
            message += f"📏 <b>Спред:</b> {spread:.2f} ({spread_percent:.2f}%)\n"
        
        message += f"⏰ <i>{timestamp}</i>"
        
        return message

# Глобальный экземпляр сервиса (для удобства)
_tinkoff_service = None

async def get_tinkoff_service():
    """Получает или создаёт экземпляр TinkoffService"""
    global _tinkoff_service
    if _tinkoff_service is None:
        _tinkoff_service = TinkoffService()
        await _tinkoff_service.__aenter__()
    return _tinkoff_service

async def close_tinkoff_service():
    """Закрывает соединение с Tinkoff"""
    global _tinkoff_service
    if _tinkoff_service:
        await _tinkoff_service.__aexit__(None, None, None)
        _tinkoff_service = None
def format_orderbook_for_telegram(data: Dict[str, Any]) -> str:
    """Статическая функция для форматирования стакана"""
    if not data:
        return "❌ Не удалось получить данные стакана"
    
    # Создаём заголовок
    timestamp = data['timestamp'].strftime('%H:%M:%S')
    message = f"📊 <b>СТАКАН {data['ticker']}</b>\n"
    message += f"<i>{data['name']}</i>\n\n"
    
    # Продажа (asks)
    if data['asks']:
        message += "💰 <b>ПРОДАЖА:</b>\n"
        for ask in data['asks'][:5]:  # Только первые 5 уровней
            message += f"  {ask['price']:>8.2f} | {ask['quantity']:>6} лотов\n"
    else:
        message += "💰 <b>ПРОДАЖА:</b> нет данных\n"
    
    message += "\n"
    
    # Покупка (bids)
    if data['bids']:
        message += "🛒 <b>ПОКУПКА:</b>\n"
        for bid in data['bids'][:5]:
            message += f"  {bid['price']:>8.2f} | {bid['quantity']:>6} лотов\n"
    else:
        message += "🛒 <b>ПОКУПКА:</b> нет данных\n"
    
    message += "\n"
    
    # Спред и время
    if data['best_bid'] and data['best_ask']:
        spread = data['best_ask'] - data['best_bid']
        spread_percent = (spread / data['best_bid']) * 100
        message += f"💎 <b>Спрос:</b> {data['best_bid']:.2f}\n"
        message += f"💎 <b>Предложение:</b> {data['best_ask']:.2f}\n"
        message += f"📏 <b>Спред:</b> {spread:.2f} ({spread_percent:.2f}%)\n"
    
    message += f"⏰ <i>{timestamp}</i>"
    
    return message
