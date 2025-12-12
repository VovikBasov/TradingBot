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

    def calculate_spread(self, data: Dict[str, Any]) -> str:
        """Рассчитывает спред между лучшей ценой продажи и покупки"""
        if not data.get('asks') or not data.get('bids'):
            return ""  # Нет данных для расчета спреда
        
        try:
            # Лучшая цена продажи (самая низкая в asks)
            best_ask = min(ask['price'] for ask in data['asks'])
            # Лучшая цена покупки (самая высокая в bids)
            best_bid = max(bid['price'] for bid in data['bids'])
            
            # Рассчитываем спред
            spread = best_ask - best_bid
            
            # Форматируем вывод
            return f"📏 <b>Spread:</b> {spread:.2f}"
        
        except (ValueError, KeyError) as e:
            return ""  # Если что-то пошло не так, просто не показываем спред

    def format_orderbook_for_telegram(self, data: Dict[str, Any]) -> str:
        """Форматирует стакан для Telegram (с лучшими ценами и спредом)"""
        if not data or (not data['asks'] and not data['bids']):
            return f"❌ Не удалось получить стакан для {data.get('ticker', 'тикера')} или стакан пуст."
        timestamp = data['timestamp'].strftime('%H:%M:%S')
        message = f"<b>{data['ticker']} | {data['name']} | {timestamp}</b>\n"
        message += "══════════════════════════════\n"
        
        if data['asks']:
            message += "<b>SELL:</b>\n"
            # СОРТИРУЕМ ASKS ОТ БОЛЬШЕЙ ЦЕНЫ К МЕНЬШЕЙ (для продажи сначала самые выгодные цены)
            sorted_asks = sorted(data['asks'], key=lambda x: x['price'], reverse=True)
            for ask in sorted_asks[:data['depth']]:
                message += f"{ask['price']:>8.2f} | {ask['quantity']:>5} лотов\n"
        else:
            message += "<b>SELL:</b> нет данных\n"
        
        message += "\n"
        
        if data['bids']:
            message += "<b>BUY:</b>\n"
            # BIDS оставляем от большей цены к меньшей (для покупки сначала самые выгодные цены)
            sorted_bids = sorted(data['bids'], key=lambda x: x['price'], reverse=True)
            for bid in sorted_bids[:data['depth']]:
                message += f"{bid['price']:>8.2f} | {bid['quantity']:>5} лотов\n"
        else:
            message += "<b>BUY:</b> нет данных\n"
        
        # РАССЧИТЫВАЕМ И ДОБАВЛЯЕМ СПРЕД
        spread_text = self.calculate_spread(data)
        if spread_text:
            message += "\n" + spread_text
        
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
