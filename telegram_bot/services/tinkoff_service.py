#!/usr/bin/env python3
"""
Сервис для работы с Tinkoff API (ТОЛЬКО СТАКАН, упрощенная версия)
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

try:
    from tinkoff.invest import Client
    print("✅ Tinkoff библиотеки импортированы")
except ImportError as e:
    print(f"❌ Ошибка импорта Tinkoff: {e}")
    raise

class TinkoffService:
    def __init__(self):
        self.token = os.getenv('INVEST_TOKEN')
        if not self.token:
            raise ValueError("❌ Токен Tinkoff API не найден в .env файле")
        print("🚀 TinkoffService инициализирован (версия: ТОЛЬКО СТАКАН)")

    async def find_instrument_by_ticker(self, ticker: str):
        return await asyncio.to_thread(self._find_instrument_by_ticker_sync, ticker)

    def _find_instrument_by_ticker_sync(self, ticker: str):
        try:
            with Client(self.token) as client:
                found_instruments = client.instruments.find_instrument(query=ticker)
                if not found_instruments.instruments:
                    print(f"❌ Инструмент с тикером '{ticker}' не найден")
                    return None
                for instrument in found_instruments.instruments:
                    if instrument.ticker == ticker:
                        print(f"✅ Найден инструмент: {instrument.name} ({instrument.ticker})")
                        return instrument
                print(f"❌ Точное совпадение для тикера '{ticker}' не найдено")
                return None
        except Exception as e:
            print(f"❌ Ошибка поиска инструмента '{ticker}': {e}")
            import traceback
            print(f"Подробности: {traceback.format_exc()}")
            return None

    async def get_orderbook(self, ticker: str, depth: int = 5) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._get_orderbook_sync, ticker, depth)

    def _get_orderbook_sync(self, ticker: str, depth: int = 5) -> Optional[Dict[str, Any]]:
        """Синхронное получение стакана (ТОЛЬКО bids и asks)"""
        try:
            instrument = self._find_instrument_by_ticker_sync(ticker)
            if not instrument:
                return None
            print(f"📊 Запрашиваем стакан для '{ticker}' (глубина: {depth})...")
            with Client(self.token) as client:
                api_response = client.market_data.get_order_book(figi=instrument.figi, depth=depth)
            orderbook_obj = api_response.orderbook if hasattr(api_response, 'orderbook') else api_response
            print(f"   Ответ типа: {type(orderbook_obj).__name__}")
            result = {
                'ticker': ticker,
                'name': instrument.name,
                'asks': [],
                'bids': [],
                'timestamp': datetime.now(),
                'depth': depth
            }
            if hasattr(orderbook_obj, 'asks') and orderbook_obj.asks:
                for ask in orderbook_obj.asks[:depth]:
                    result['asks'].append({
                        'price': self._quotation_to_float(ask.price),
                        'quantity': ask.quantity
                    })
            if hasattr(orderbook_obj, 'bids') and orderbook_obj.bids:
                for bid in orderbook_obj.bids[:depth]:
                    result['bids'].append({
                        'price': self._quotation_to_float(bid.price),
                        'quantity': bid.quantity
                    })
            print(f"✅ Данные стакана '{ticker}' получены")
            return result
        except Exception as e:
            print(f"❌ Ошибка получения стакана '{ticker}': {e}")
            import traceback
            traceback.print_exc()
            return None

    def _quotation_to_float(self, quotation) -> float:
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0

    def format_orderbook_for_telegram(self, data: Dict[str, Any]) -> str:
        """Форматирует ТОЛЬКО стакан для Telegram (без лучших цен и спреда)"""
        if not data or (not data['asks'] and not data['bids']):
            return f"❌ Не удалось получить стакан для {data.get('ticker', 'тикера')} или стакан пуст."
        timestamp = data['timestamp'].strftime('%H:%M:%S')
        message = f"<b>{data['ticker']} | {data['name']} | {timestamp}</b>\n"
        message += "══════════════════════════════\n"
        if data['asks']:
            message += "<b>SELL:</b>\n"
            for ask in data['asks']:
                message += f"{ask['price']:>8.2f} | {ask['quantity']:>5} лотов\n"
        else:
            message += "<b>SELL:</b> нет данных\n"
        message += "\n"
        if data['bids']:
            message += "<b>BUY:</b>\n"
            for bid in data['bids']:
                message += f"{bid['price']:>8.2f} | {bid['quantity']:>5} лотов\n"
        else:
            message += "<b>BUY:</b> нет данных\n"
        return message

# Глобальный экземпляр сервиса
_tinkoff_service = None
async def get_tinkoff_service():
    global _tinkoff_service
    if _tinkoff_service is None:
        _tinkoff_service = TinkoffService()
    return _tinkoff_service
async def close_tinkoff_service():
    global _tinkoff_service
    _tinkoff_service = None
def format_orderbook_for_telegram(data: Dict[str, Any]) -> str:
    if not data:
        return "❌ Не удалось получить данные стакана."
    service = TinkoffService()
    return service.format_orderbook_for_telegram(data)
