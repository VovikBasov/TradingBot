#!/usr/bin/env python3
"""
Tinkoff gRPC клиент для получения стакана - ИСПРАВЛЕННАЯ ВЕРСИЯ 2
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import log

# Импортируем proto-модули Tinkoff
try:
    from tinkoff.invest import Client, AsyncClient
    from tinkoff.invest.schemas import InstrumentStatus, InstrumentIdType
    log.info("✅ Tinkoff библиотеки импортированы")
except ImportError as e:
    log.error(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

class TinkoffGrpcFastClient:
    """
    Быстрый gRPC клиент для Tinkoff API
    Использует асинхронные вызовы и стриминг
    """
    
    def __init__(self, token=None):
        """
        Инициализация gRPC клиента
        """
        self.token = token or os.getenv('INVEST_TOKEN')
        if not self.token:
            log.error("❌ Токен не найден. Укажите в .env файле")
            raise ValueError("Токен Tinkoff API не найден")
        
        log.info("🚀 Инициализация быстрого gRPC клиента Tinkoff")
    
    def find_instrument_by_ticker_sync(self, ticker: str):
        """
        Синхронный поиск инструмента (ИСПРАВЛЕННЫЙ ВАРИАНТ)
        Ключевое исправление: получаем полный инструмент через get_instrument_by()
        """
        try:
            with Client(self.token) as client:
                # 1. Сначала находим инструмент через find_instrument
                found_instruments = client.instruments.find_instrument(query=ticker)
                
                if not found_instruments.instruments:
                    log.error(f"❌ Инструмент с тикером '{ticker}' не найден")
                    return None
                
                # 2. Ищем точное совпадение по тикеру
                target_instrument = None
                for instrument in found_instruments.instruments:
                    if instrument.ticker == ticker:
                        target_instrument = instrument
                        log.info(f"🔍 Найден тикер '{ticker}', получаем полные данные...")
                        break
                
                if not target_instrument:
                    log.error(f"❌ Точное совпадение для тикера '{ticker}' не найдено")
                    return None
                
                # 3. Получаем ПОЛНЫЙ инструмент через get_instrument_by
                # Используем FIGI, если есть, иначе uid
                if hasattr(target_instrument, 'figi') and target_instrument.figi:
                    full_instrument = client.instruments.get_instrument_by(
                        id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                        id=target_instrument.figi
                    )
                elif hasattr(target_instrument, 'uid') and target_instrument.uid:
                    full_instrument = client.instruments.get_instrument_by(
                        id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
                        id=target_instrument.uid
                    )
                else:
                    log.error(f"❌ Не удалось определить ID для инструмента '{ticker}'")
                    return None
                
                # 4. Проверяем, что инструмент активен
                if full_instrument.instrument.state == InstrumentStatus.INSTRUMENT_STATUS_BASE:
                    log.info(f"✅ Найден активный инструмент: {full_instrument.instrument.name} ({full_instrument.instrument.ticker})")
                    return full_instrument.instrument
                else:
                    log.warning(f"⚠️  Инструмент найден, но неактивен: {full_instrument.instrument.name}, статус: {full_instrument.instrument.state}")
                    return full_instrument.instrument
                
        except Exception as e:
            log.error(f"❌ Ошибка поиска инструмента '{ticker}': {e}")
            import traceback
            log.error(f"Подробности: {traceback.format_exc()}")
            return None
    
    def get_orderbook_snapshot_sync(self, ticker: str, depth: int = 5):
        """
        Синхронный запрос стакана (основной рабочий метод)
        """
        log.info(f"📊 Запрашиваем стакан для '{ticker}'...")
        instrument = self.find_instrument_by_ticker_sync(ticker)
        
        if not instrument:
            log.error(f"❌ Не удалось найти инструмент '{ticker}' для стакана")
            return None
        
        try:
            start_time = datetime.now()
            
            with Client(self.token) as client:
                # Получаем стакан
                orderbook = client.market_data.get_order_book(
                    figi=instrument.figi,
                    depth=depth
                )
            
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
        """Конвертирует Quotation в float"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def print_pretty_orderbook(self, data):
        """
        Красиво печатает стакан
        """
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
        
        # Аски (продажа) - сверху
        if orderbook.asks:
            print("💰 ПРОДАЖА (asks):")
            for ask in orderbook.asks[:5]:
                price = self._quotation_to_float(ask.price)
                quantity = ask.quantity
                print(f"  {price:10.2f} | {quantity:6} лотов")
        else:
            print("💰 ПРОДАЖА: пусто")
        
        print(f"{'-'*30}")
        
        # Биды (покупка) - снизу
        if orderbook.bids:
            print("🛒 ПОКУПКА (bids):")
            for bid in orderbook.bids[:5]:
                price = self._quotation_to_float(bid.price)
                quantity = bid.quantity
                print(f"  {price:10.2f} | {quantity:6} лотов")
        else:
            print("🛒 ПОКУПКА: пусто")
        
        print(f"{'='*60}")
        
        # Лучшие цены
        if orderbook.best_bid_price and orderbook.best_ask_price:
            spread = self._quotation_to_float(orderbook.best_ask_price) - self._quotation_to_float(orderbook.best_bid_price)
            spread_percent = (spread / self._quotation_to_float(orderbook.best_bid_price)) * 100
            print(f"💎 Лучший спрос:   {self._quotation_to_float(orderbook.best_bid_price):.2f}")
            print(f"💎 Лучшее предложение: {self._quotation_to_float(orderbook.best_ask_price):.2f}")
            print(f"📏 Спред: {spread:.2f} ({spread_percent:.2f}%)")
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
            print(f"   Статус: {instrument.state}")
            print(f"   Лот: {instrument.lot}")
            return True
        else:
            print(f"❌ Инструмент '{ticker}' не найден")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def simple_test():
    """Простой тест напрямую через API"""
    print("🧪 Простой тест API...")
    try:
        from tinkoff.invest import Client
        from tinkoff.invest.schemas import InstrumentIdType
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        token = os.getenv('INVEST_TOKEN')
        
        with Client(token) as client:
            # Ищем SBER
            instruments = client.instruments.find_instrument(query="SBER")
            print(f"🔍 Найдено инструментов: {len(instruments.instruments)}")
            
            for i, instr in enumerate(instruments.instruments[:3]):
                print(f"\nИнструмент {i+1}:")
                print(f"  Тип: {type(instr)}")
                print(f"  Тикер: {instr.ticker}")
                print(f"  Название: {instr.name}")
                print(f"  Атрибуты: {[attr for attr in dir(instr) if not attr.startswith('_')]}")
                
                # Пробуем получить полный инструмент если есть FIGI
                if hasattr(instr, 'figi') and instr.figi:
                    try:
                        full = client.instruments.get_instrument_by(
                            id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                            id=instr.figi
                        )
                        print(f"  ✅ Полный инструмент получен!")
                        print(f"     Статус: {full.instrument.state}")
                    except Exception as e:
                        print(f"  ❌ Ошибка получения полного инструмента: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка простого теста: {e}")
        return False

# ТОЧКА ВХОДА
# ===========

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("""
📡 Tinkoff gRPC Client v2 - Быстрое получение стакана
Использование:
  python scripts/tinkoff_grpc_client_fixed.py <команда> [тикер] [глубина]

Команды:
  test [тикер]       - Тест подключения и поиска инструмента
  get [тикер] [глуб] - Получить стакан (глубина по умолчанию: 5)
  simple             - Простой тест API напрямую
  
Примеры:
  python scripts/tinkoff_grpc_client_fixed.py test SBER
  python scripts/tinkoff_grpc_client_fixed.py get GAZP 10
  python scripts/tinkoff_grpc_client_fixed.py simple
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
    
    elif command == "simple":
        simple_test()
    
    else:
        print(f"❌ Неизвестная команда: {command}")

if __name__ == "__main__":
    main()
