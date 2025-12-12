#!/usr/bin/env python3
"""
Tinkoff gRPC клиент для получения стакана - ФИНАЛЬНАЯ РАБОЧАЯ ВЕРСИЯ
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
        """ФИНАЛЬНАЯ версия поиска инструмента"""
        try:
            with Client(self.token) as client:
                found_instruments = client.instruments.find_instrument(query=ticker)
                
                if not found_instruments.instruments:
                    log.error(f"❌ Инструмент с тикером '{ticker}' не найден")
                    return None
                
                # Простой и надежный фильтр
                for instrument in found_instruments.instruments:
                    # 1. Главное условие - точное совпадение тикера
                    if instrument.ticker != ticker:
                        continue
                    # 2. Инструмент должен быть доступен для торговли через API
                    if not getattr(instrument, 'api_trade_available_flag', False):
                        log.warning(f"⚠️  Инструмент '{ticker}' найден, но недоступен для торговли через API.")
                        # Можно продолжить поиск или вернуть None
                        continue
                    # 3. (ОПЦИОНАЛЬНО) Можно фильтровать по классу кода, чтобы брать именно акции с MOEX
                    # 'TQBR' - акции, 'FUT' - фьючерсы и т.д.
                    # if getattr(instrument, 'class_code', '') not in ['TQBR', 'TQTD']:
                    #     continue
                    
                    # Если дошли сюда - инструмент подходит
                    log.info(f"✅ Найден подходящий инструмент: {instrument.name} ({instrument.ticker}), FIGI: {instrument.figi}")
                    return instrument
                
                # Если ни один инструмент не прошел фильтр
                log.error(f"❌ Не найден доступный для торговли инструмент с тикером '{ticker}'")
                return None
                
        except Exception as e:
            log.error(f"❌ Ошибка поиска инструмента '{ticker}': {e}")
            import traceback
            traceback.print_exc()
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
                orderbook = client.market_data.get_order_book(figi=instrument.figi, depth=depth)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            result = {
                'ticker': ticker,
                'instrument': instrument,
                'orderbook': orderbook,
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
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0

    def print_pretty_orderbook(self, data):
        if not data:
            print(f"❌ Нет данных стакана")
            return
        orderbook = data['orderbook']
        instrument = data['instrument']
        print(f"\n{'='*60}")
        print(f"📊 СТАКАН {data['ticker']} ({instrument.name})")
        print(f"⏰ {data['timestamp'].strftime('%H:%M:%S')} | 📡 {data['source']}")
        print(f"⚡ Время ответа: {data.get('response_time_ms', 0):.1f} мс")
        print(f"{'='*60}")
        if orderbook.asks:
            print("💰 ПРОДАЖА (asks):")
            for ask in orderbook.asks[:5]:
                price = self._quotation_to_float(ask.price)
                print(f"  {price:10.2f} | {ask.quantity:6} лотов")
        else:
            print("💰 ПРОДАЖА: пусто")
        print(f"{'-'*30}")
        if orderbook.bids:
            print("🛒 ПОКУПКА (bids):")
            for bid in orderbook.bids[:5]:
                price = self._quotation_to_float(bid.price)
                print(f"  {price:10.2f} | {bid.quantity:6} лотов")
        else:
            print("🛒 ПОКУПКА: пусто")
        print(f"{'='*60}")
        if orderbook.best_bid_price and orderbook.best_ask_price:
            spread = self._quotation_to_float(orderbook.best_ask_price) - self._quotation_to_float(orderbook.best_bid_price)
            spread_percent = (spread / self._quotation_to_float(orderbook.best_bid_price)) * 100
            print(f"💎 Лучший спрос:   {self._quotation_to_float(orderbook.best_bid_price):.2f}")
            print(f"💎 Лучшее предложение: {self._quotation_to_float(orderbook.best_ask_price):.2f}")
            print(f"📏 Спред: {spread:.2f} ({spread_percent:.2f}%)")
        print(f"{'='*60}")

def get_orderbook_sync(ticker="SBER", depth=5):
    client = TinkoffGrpcFastClient()
    data = client.get_orderbook_snapshot_sync(ticker, depth)
    if data:
        client.print_pretty_orderbook(data)
    else:
        print(f"❌ Не удалось получить стакан {ticker}")

def test_connection_sync(ticker="SBER"):
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

def main():
    if len(sys.argv) < 2:
        print("""
📡 Tinkoff gRPC Client - Финальная версия
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
