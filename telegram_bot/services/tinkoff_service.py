#!/usr/bin/env python3
"""
Сервис для работы с Tinkoff API (финальная исправленная версия)
Логика поиска унифицирована с scripts/tinkoff_grpc_client_fixed.py
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
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
        print("🚀 TinkoffService инициализирован (финальная версия, логика поиска исправлена)")

    async def find_instrument_by_ticker(self, ticker: str):
        return await asyncio.to_thread(self._find_instrument_by_ticker_sync, ticker)

    def _find_instrument_by_ticker_sync(self, ticker: str):
        """Синхронный поиск инструмента по тикеру (УПРОЩЕННЫЙ, как в основном скрипте)"""
        try:
            with Client(self.token) as client:
                found_instruments = client.instruments.find_instrument(query=ticker)
                if not found_instruments.instruments:
                    print(f"❌ Инструмент с тикером '{ticker}' не найден")
                    return None

                # 1. Берем первый инструмент с точным совпадением тикера
                for instrument in found_instruments.instruments:
                    if instrument.ticker == ticker:
                        # 2. Проверяем, доступен ли для торговли через API (опционально, но желательно)
                        if getattr(instrument, 'api_trade_available_flag', False):
                            print(f"✅ Найден подходящий инструмент: {instrument.name} ({instrument.ticker})")
                            return instrument
                        else:
                            # Если недоступен, все равно возвращаем для получения стакана (FIGI есть)
                            print(f"⚠️  Инструмент '{ticker}' найден, но недоступен для торговли через API.")
                            return instrument

                # 3. Если точного совпадения нет, возвращаем первый попавшийся (на случай нестандартного тикера)
                if found_instruments.instruments:
                    first_instr = found_instruments.instruments[0]
                    print(f"⚠️  Точное совпадение для '{ticker}' не найдено. Берем первый: {first_instr.name} ({first_instr.ticker})")
                    return first_instr

                print(f"❌ Акция '{ticker}' не найдена")
                return None

        except Exception as e:
            print(f"❌ Ошибка поиска инструмента '{ticker}': {e}")
            import traceback
            print(f"Подробности: {traceback.format_exc()}")
            return None

    async def get_orderbook(self, ticker: str, depth: int = 5) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._get_orderbook_sync, ticker, depth)

    def _get_orderbook_sync(self, ticker: str, depth: int = 5) -> Optional[Dict[str, Any]]:
        try:
            instrument = self._find_instrument_by_ticker_sync(ticker)
            if not instrument:
                return None
            print(f"📊 Запрашиваем стакан для '{ticker}' (глубина: {depth})...")

            with Client(self.token) as client:
                response = client.market_data.get_order_book(figi=instrument.figi, depth=depth)
                orderbook_obj = response.orderbook

            # Форматируем результат
            result = {
                'ticker': ticker,
                'name': instrument.name,
                'figi': instrument.figi,
                'asks': [],
                'bids': [],
                'best_bid': None,
                'best_ask': None,
                'timestamp': datetime.now(),
                'depth': depth
            }

            if orderbook_obj.asks:
                result['best_ask'] = self._quotation_to_float(orderbook_obj.best_ask_price)
                for ask in orderbook_obj.asks[:depth]:
                    result['asks'].append({
                        'price': self._quotation_to_float(ask.price),
                        'quantity': ask.quantity
                    })

            if orderbook_obj.bids:
                result['best_bid'] = self._quotation_to_float(orderbook_obj.best_bid_price)
                for bid in orderbook_obj.bids[:depth]:
                    result['bids'].append({
                        'price': self._quotation_to_float(bid.price),
                        'quantity': bid.quantity
                    })

            print(f"✅ Стакан '{ticker}' получен успешно")
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
        if not data:
            return "❌ Не удалось получить данные стакана"
        timestamp = data['timestamp'].strftime('%H:%M:%S')
        message = f"📊 <b>СТАКАН {data['ticker']}</b>\n<i>{data['name']}</i>\n\n"
        if data['asks']:
            message += "💰 <b>ПРОДАЖА:</b>\n"
            for ask in data['asks'][:5]:
                message += f"  {ask['price']:>8.2f} | {ask['quantity']:>6} лотов\n"
        else:
            message += "💰 <b>ПРОДАЖА:</b> нет данных\n"
        message += "\n"
        if data['bids']:
            message += "🛒 <b>ПОКУПКА:</b>\n"
            for bid in data['bids'][:5]:
                message += f"  {bid['price']:>8.2f} | {bid['quantity']:>6} лотов\n"
        else:
            message += "🛒 <b>ПОКУПКА:</b> нет данных\n"
        message += "\n"
        if data['best_bid'] and data['best_ask']:
            spread = data['best_ask'] - data['best_bid']
            spread_percent = (spread / data['best_bid']) * 100 if data['best_bid'] != 0 else 0
            message += f"💎 <b>Спрос:</b> {data['best_bid']:.2f}\n"
            message += f"💎 <b>Предложение:</b> {data['best_ask']:.2f}\n"
            message += f"📏 <b>Спред:</b> {spread:.2f} ({spread_percent:.2f}%)\n"
        message += f"⏰ <i>{timestamp} | Глубина: {data.get('depth', 5)}</i>"
        return message

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
