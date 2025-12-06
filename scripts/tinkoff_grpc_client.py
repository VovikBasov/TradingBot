#!/usr/bin/env python3
"""
Tinkoff gRPC клиент для получения стакана
Быстрее и эффективнее REST версии
Запуск: python scripts/tinkoff_grpc_client.py SBER
"""

import os
import sys
import grpc
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
    from tinkoff.invest import AsyncClient
    from tinkoff.invest.schemas import InstrumentStatus, GetOrderBookRequest
    from tinkoff.invest.services import MarketDataStreamManager
    log.info("✅ Tinkoff библиотеки импортированы")
except ImportError as e:
    log.error(f"❌ Ошибка импорта: {e}")
    print("Установите библиотеку: pip install tinkoff-invest")
    sys.exit(1)

class TinkoffGrpcFastClient:
    """
    Быстрый gRPC клиент для Tinkoff API
    Использует асинхронные вызовы и стриминг
    """
    
    def __init__(self, token=None):
        """
        Инициализация gRPC клиента
        
        Args:
            token: Токен Tinkoff Invest API
                  Если не указан, берётся из .env файла
        """
        self.token = token or os.getenv('INVEST_TOKEN')
        if not self.token:
            log.error("❌ Токен не найден. Укажите в .env файле или передайте в конструктор")
            raise ValueError("Токен Tinkoff API не найден")
        
        log.info("🚀 Инициализация быстрого gRPC клиента Tinkoff")
        self._client = None
        
    async def __aenter__(self):
        """Контекстный менеджер для асинхронного клиента"""
        self._client = AsyncClient(self.token)
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Завершение работы клиента"""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def find_instrument_by_ticker(self, ticker: str):
        """
        Быстрый поиск инструмента по тикеру через gRPC
        
        Args:
            ticker: Тикер инструмента (например, 'SBER')
            
        Returns:
            Инструмент или None если не найден
        """
        try:
            instruments = await self._client.instruments.find_instrument(query=ticker)
            
            for instrument in instruments.instruments:
                if (instrument.ticker == ticker and 
                    instrument.state == InstrumentStatus.INSTRUMENT_STATUS_BASE):
                    log.info(f"✅ Найден инструмент: {instrument.name} ({instrument.ticker})")
                    return instrument
            
            log.warning(f"⚠️ Инструмент {ticker} не найден в активных")
            
            # Попробуем найти любой инструмент с таким тикером
            for instrument in instruments.instruments:
                if instrument.ticker == ticker:
                    log.info(f"📝 Инструмент найден, но статус: {instrument.state}")
                    return instrument
                    
            return None
            
        except Exception as e:
            log.error(f"❌ Ошибка поиска инструмента {ticker}: {e}")
            return None
    
    async def get_orderbook_stream(self, ticker: str, depth: int = 10):
        """
        Получаем стакан в реальном времени через gRPC стрим
        
        Args:
            ticker: Тикер инструмента
            depth: Глубина стакана
            
        Returns:
            Асинхронный генератор стаканов
        """
        instrument = await self.find_instrument_by_ticker(ticker)
        if not instrument:
            log.error(f"❌ Не удалось найти инструмент {ticker}")
            return
        
        log.info(f"📊 Подключаемся к стриму стакана {ticker} (FIGI: {instrument.figi})")
        
        # Создаем менеджер стрима
        stream_manager = MarketDataStreamManager(self._client)
        
        try:
            async with stream_manager as stream:
                # Подписываемся на стакан
                await stream.order_book.subscribe(
                    instrument.figi,
                    depth=depth
                )
                
                log.info(f"✅ Подписка на стакан {ticker} активирована")
                print(f"\n🎯 СТРИМ СТАКАНА: {ticker}")
                print("Для остановки нажмите Ctrl+C\n")
                
                # Получаем обновления стакана
                async for orderbook in stream:
                    yield self._format_orderbook(orderbook, ticker)
                    
        except asyncio.CancelledError:
            log.info("⏹️ Стрим остановлен пользователем")
        except Exception as e:
            log.error(f"❌ Ошибка в стриме: {e}")
    
    async def get_orderbook_snapshot(self, ticker: str, depth: int = 10):
        """
        Быстрый однократный запрос стакана через gRPC
        
        Args:
            ticker: Тикер инструмента
            depth: Глубина стакана
            
        Returns:
            Словарь с данными стакана
        """
        instrument = await self.find_instrument_by_ticker(ticker)
        if not instrument:
            return None
        
        try:
            start_time = datetime.now()
            
            # Быстрый gRPC запрос
            orderbook = await self._client.market_data.get_order_book(
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
                'source': 'gRPC'
            }
            
            log.info(f"📊 Стакан {ticker} получен за {response_time:.1f} мс")
            return result
            
        except Exception as e:
            log.error(f"❌ Ошибка получения стакана {ticker}: {e}")
            return None
    
    def _format_orderbook(self, orderbook_data, ticker: str):
        """
        Форматирует данные стакана для вывода
        
        Returns:
            Отформатированные данные
        """
        if not orderbook_data or not hasattr(orderbook_data, 'orderbook'):
            return None
        
        orderbook = orderbook_data.orderbook
        
        # Собираем биды и аски
        bids = []
        asks = []
        
        if orderbook.bids:
            for bid in orderbook.bids[:5]:  # Только первые 5
                price = self._quotation_to_float(bid.price)
                quantity = bid.quantity
                bids.append((price, quantity))
        
        if orderbook.asks:
            for ask in orderbook.asks[:5]:
                price = self._quotation_to_float(ask.price)
                quantity = ask.quantity
                asks.append((price, quantity))
        
        return {
            'ticker': ticker,
            'timestamp': datetime.now(),
            'bids': bids,
            'asks': asks,
            'best_bid': self._quotation_to_float(orderbook.best_bid_price) if orderbook.best_bid_price else None,
            'best_ask': self._quotation_to_float(orderbook.best_ask_price) if orderbook.best_ask_price else None,
            'depth': len(orderbook.bids) + len(orderbook.asks)
        }
    
    def _quotation_to_float(self, quotation):
        """Конвертирует Quotation в float"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0
    
    def print_pretty_orderbook(self, data):
        """
        Красиво печатает стакан
        
        Args:
            data: Данные стакана из get_orderbook_snapshot
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
            for ask in orderbook.asks[:5]:  # Первые 5 уровней
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

async def get_orderbook_async(ticker="SBER", depth=5):
    """Асинхронное получение стакана"""
    async with TinkoffGrpcFastClient() as client:
        data = await client.get_orderbook_snapshot(ticker, depth)
        if data:
            client.print_pretty_orderbook(data)
        else:
            print(f"❌ Не удалось получить стакан {ticker}")

async def stream_orderbook_async(ticker="SBER", depth=5, limit=10):
    """Асинхронный стрим стакана"""
    client = TinkoffGrpcFastClient()
    async with client as grpc_client:
        count = 0
        try:
            async for orderbook in grpc_client.get_orderbook_stream(ticker, depth):
                if orderbook:
                    print(f"\n📈 Обновление #{count+1} - {ticker}")
                    print(f"⏰ {orderbook['timestamp'].strftime('%H:%M:%S.%f')[:-3]}")
                    
                    if orderbook['asks']:
                        print("💰 Продажа:")
                        for price, qty in orderbook['asks']:
                            print(f"  {price:10.2f} | {qty:6} лотов")
                    
                    if orderbook['bids']:
                        print("🛒 Покупка:")
                        for price, qty in orderbook['bids']:
                            print(f"  {price:10.2f} | {qty:6} лотов")
                    
                    if orderbook['best_bid'] and orderbook['best_ask']:
                        spread = orderbook['best_ask'] - orderbook['best_bid']
                        print(f"📏 Спред: {spread:.2f}")
                    
                    count += 1
                    if limit and count >= limit:
                        print(f"\n✅ Получено {limit} обновлений")
                        break
                        
        except KeyboardInterrupt:
            print(f"\n⏹️ Остановлено пользователем. Получено обновлений: {count}")

# СИНХРОННЫЕ ОБЕРТКИ ДЛЯ ЗАПУСКА ИЗ КОМАНДНОЙ СТРОКИ
# ====================================================

def get_orderbook(ticker="SBER", depth=5):
    """Синхронная обертка для получения стакана"""
    try:
        asyncio.run(get_orderbook_async(ticker, depth))
    except KeyboardInterrupt:
        print("\n⏹️ Операция прервана")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def stream_orderbook(ticker="SBER", depth=5, limit=None):
    """Синхронная обертка для стрима стакана"""
    try:
        asyncio.run(stream_orderbook_async(ticker, depth, limit))
    except KeyboardInterrupt:
        print("\n⏹️ Поток остановлен")
    except Exception as e:
        print(f"❌ Ошибка в потоке: {e}")

def test_connection():
    """Тест подключения к gRPC"""
    print("🧪 Тестируем gRPC подключение к Tinkoff...")
    try:
        asyncio.run(test_connection_async())
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def test_connection_async():
    """Асинхронный тест подключения"""
    async with TinkoffGrpcFastClient() as client:
        print("✅ gRPC клиент инициализирован")
        
        # Тестируем поиск SBER
        instrument = await client.find_instrument_by_ticker("SBER")
        if instrument:
            print(f"✅ Инструмент найден: {instrument.name}")
            return True
        else:
            print("❌ Инструмент не найден")
            return False

# ТОЧКА ВХОДА
# ===========

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("""
📡 Tinkoff gRPC Client - Быстрое получение стакана
Использование:
  python scripts/tinkoff_grpc_client.py <команда> [параметры]

Команды:
  get <тикер> [глубина]     - Однократный запрос стакана
  stream <тикер> [глубина]  - Потоковый стакан (Ctrl+C для остановки)
  test                      - Тест подключения
  
Примеры:
  python scripts/tinkoff_grpc_client.py get SBER 10
  python scripts/tinkoff_grpc_client.py stream GAZP 5
  python scripts/tinkoff_grpc_client.py test
        """)
        return
    
    command = sys.argv[1].lower()
    
    if command == "get":
        ticker = sys.argv[2] if len(sys.argv) > 2 else "SBER"
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        get_orderbook(ticker, depth)
    
    elif command == "stream":
        ticker = sys.argv[2] if len(sys.argv) > 2 else "SBER"
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
        stream_orderbook(ticker, depth, limit)
    
    elif command == "test":
        test_connection()
    
    else:
        print(f"❌ Неизвестная команда: {command}")
        print("Доступные команды: get, stream, test")

if __name__ == "__main__":
    main()
