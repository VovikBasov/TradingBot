#!/usr/bin/env python3
"""
Tinkoff gRPC клиент для получения стакана - ИСПРАВЛЕННАЯ ВЕРСИЯ (синхронизирована с ботом)
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import log

try:
    from tinkoff.invest import Client
    log.info("✅ Tinkoff библиотеки импортированы")
except ImportError as e:
    log.error(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

class TinkoffGrpcFastClient:
    def __init__(self, token=None):
        self.token = token or os.getenv('INVEST_TOKEN')
        if not self.token:
            log.error("❌ Токен не найден. Укажите в .env файле")
            raise ValueError("Токен Tinkoff API не найден")
        log.info("🚀 Инициализация gRPC клиента Tinkoff")

    def find_instrument_by_ticker_sync(self, ticker: str):
        """Синхронный поиск инструмента по тикеру"""
        try:
            with Client(self.token) as client:
                found_instruments = client.instruments.find_instrument(query=ticker)
                if not found_instruments.instruments:
                    log.error(f"❌ Инструмент с тикером '{ticker}' не найден")
                    return None

                # Берем первый инструмент с точным совпадением тикера
                for instrument in found_instruments.instruments:
                    if instrument.ticker == ticker:
                        if getattr(instrument, 'api_trade_available_flag', False):
                            log.info(f"✅ Найден подходящий инструмент: {instrument.name} ({instrument.ticker}), FIGI: {instrument.figi}")
                        else:
                            log.info(f"⚠️  Инструмент '{ticker}' найден, но недоступен для торговли через API.")
                        return instrument

                log.error(f"❌ Точное совпадение для тикера '{ticker}' не найдено")
                return None

        except Exception as e:
            log.error(f"❌ Ошибка поиска инструмента '{ticker}': {e}")
            import traceback
            log.error(f"Подробности: {traceback.format_exc()}")
            return None

    def get_orderbook_snapshot_sync(self, ticker: str, depth: int = 5):
        log.info(f"📊 Запрашиваем стакан для '{ticker}'...")
        instrument = self.find_instrument_by_ticker_sync(ticker)

        if not instrument:
            log.error(f"❌ Не удалось найти инструмент '{ticker}' для стакана")
            return None

        try:
            start_time = datetime.now()

            with Client(self.token) as client:
                # Получаем ответ API (может быть GetOrderBookResponse или OrderBook)
                response = client.market_data.get_order_book(figi=instrument.figi, depth=depth)

            response_time = (datetime.now() - start_time).total_seconds() * 1000

            result = {
                'ticker': ticker,
                'instrument': instrument,
                'response': response,  # Сохраняем весь ответ
                'timestamp': datetime.now(),
                'response_time_ms': response_time,
                'source': 'gRPC (sync)'
            }

            log.info(f"✅ Стакан '{ticker}' получен за {response_time:.1f} мс")
            return result

        except Exception as e:
            log.error(f"❌ Ошибка получения стакана '{ticker}': {e}")
            return None

    def _quotation_to_float(self, quotation):
        """Конвертирует Quotation в float"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0

    def print_pretty_orderbook(self, data):
        """
        Красиво печатает стакан (без лучших цен и спреда)
        """
        if not data:
            print(f"❌ Нет данных стакана")
            return

        response = data['response']
        instrument = data['instrument']

        # Извлекаем объект стакана из ответа (как в боте)
        orderbook = response.orderbook if hasattr(response, 'orderbook') else response

        print(f"\n{'='*60}")
        print(f"📊 СТАКАН {data['ticker']} ({instrument.name})")
        print(f"⏰ {data['timestamp'].strftime('%H:%M:%S')} | 📡 {data['source']}")
        print(f"⚡ Время ответа: {data.get('response_time_ms', 0):.1f} мс")
        print(f"{'='*60}")

        # Аски (продажа) - сверху
        if hasattr(orderbook, 'asks') and orderbook.asks:
            print("💰 ПРОДАЖА (asks):")
            for ask in orderbook.asks[:5]:
                price = self._quotation_to_float(ask.price)
                quantity = ask.quantity
                print(f"  {price:10.2f} | {quantity:6} лотов")
        else:
            print("💰 ПРОДАЖА: пусто")

        print(f"{'-'*30}")

        # Биды (покупка) - снизу
        if hasattr(orderbook, 'bids') and orderbook.bids:
            print("🛒 ПОКУПКА (bids):")
            for bid in orderbook.bids[:5]:
                price = self._quotation_to_float(bid.price)
                quantity = bid.quantity
                print(f"  {price:10.2f} | {quantity:6} лотов")
        else:
            print("🛒 ПОКУПКА: пусто")

        print(f"{'='*60}")
        # Убрали блок с лучшими ценами и спредом
        print(f"{'='*60}")

# СИНХРОННЫЕ ФУНКЦИИ ДЛЯ КОМАНДНОЙ СТРОКИ
# ==========================================

def get_orderbook_sync(ticker="SBER", depth=5):
    """Синхронное получение стакана"""
    client = TinkoffGrpcFastClient()
    data = client.get_orderbook_snapshot_sync(ticker, depth)
    if data:
        client.print_pretty_orderbook(data)
    else:
        print(f"❌ Не удалось получить стакан {ticker}")

def test_connection_sync(ticker="SBER"):
    """Синхронный тест подключения"""
    print(f"🧪 Тестируем подключение к Tinkoff для тикера '{ticker}'...")
    try:
        client = TinkoffGrpcFastClient()
        instrument = client.find_instrument_by_ticker_sync(ticker)
        if instrument:
            print(f"✅ Инструмент найден!")
            print(f"   Название: {instrument.name}")
            print(f"   Тикер: {instrument.ticker}")
            print(f"   FIGI: {instrument.figi}")
            if hasattr(instrument, 'lot'):
                print(f"   Лот: {instrument.lot}")
            return True
        else:
            print(f"❌ Инструмент '{ticker}' не найден")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

# ТОЧКА ВХОДА
# ===========

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("""
📡 Tinkoff gRPC Client - Быстрое получение стакана
Использование:
  python scripts/tinkoff_grpc_client_fixed.py <команда> [тикер] [глубина]

Команды:
  test [тикер]       - Тест подключения и поиска инструмента
  get [тикер] [глуб] - Получить стакан (глубина по умолчанию: 5)

Примеры:
  python scripts/tinkoff_grpc_client_fixed.py test SBER
  python scripts/tinkoff_grpc_client_fixed.py get DOMRF 10
        """)
        return

    command = sys.argv[1].lower()

    if command == "test":
        ticker = sys.argv[2] if len(sys.argv) > 2 else "SBER"
        test_connection_sync(ticker)

    elif command == "get":
        ticker = sys.argv[2] if len(sys.argv) > 2 else "SBER"
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        get_orderbook_sync(ticker, depth)

    else:
        print(f"❌ Неизвестная команда: {command}")

if __name__ == "__main__":
    main()
