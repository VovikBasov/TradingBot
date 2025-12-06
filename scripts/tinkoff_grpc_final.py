#!/usr/bin/env python3
"""
РАБОЧИЙ Tinkoff gRPC клиент для получения стакана
Обходит все проблемы с API, работает с акциями MOEX
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
    from tinkoff.invest.schemas import Share
    log.info("✅ Tinkoff библиотеки импортированы")
except ImportError as e:
    log.error(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

class TinkoffGrpcWorkingClient:
    def __init__(self, token=None):
        self.token = token or os.getenv('INVEST_TOKEN')
        if not self.token:
            raise ValueError("Токен Tinkoff API не найден. Проверьте файл .env")
        log.info("🚀 Инициализация gRPC клиента Tinkoff")
    
    def find_share_by_ticker(self, ticker: str):
        """
        Находит акцию по точному тикеру на MOEX
        Обходит проблему с find_instrument, который возвращает облигации
        """
        try:
            with Client(self.token) as client:
                # Получаем ВСЕ акции (это быстрее и точнее)
                shares_response = client.instruments.shares()
                log.info(f"📋 Всего акций в базе: {len(shares_response.instruments)}")
                
                # Ищем по точному тикеру
                target_instrument = None
                for instrument in shares_response.instruments:
                    # Ищем точное совпадение тикера и фильтруем по MOEX
                    if (instrument.ticker == ticker and 
                        instrument.exchange == 'MOEX' and
                        instrument.class_code == 'TQBR'):  # Основной режим торгов акциями
                        target_instrument = instrument
                        log.info(f"✅ Найдена акция: {instrument.name} ({instrument.ticker})")
                        break
                
                if not target_instrument:
                    log.error(f"❌ Акция с тикером '{ticker}' (MOEX, TQBR) не найдена")
                    # Выведем первые несколько найденных акций для отладки
                    log.info("Доступные акции (первые 5):")
                    for inst in shares_response.instruments[:5]:
                        log.info(f"   - {inst.ticker}: {inst.name} (бир: {inst.exchange}, класс: {inst.class_code})")
                    return None
                
                return target_instrument
                
        except Exception as e:
            log.error(f"❌ Ошибка поиска акции '{ticker}': {e}")
            import traceback
            log.error(f"Подробности: {traceback.format_exc()}")
            return None
    
    def get_orderbook_sync(self, ticker: str, depth: int = 5):
        """
        Синхронный запрос стакана
        """
        log.info(f"📊 Запрашиваем стакан для '{ticker}'...")
        instrument = self.find_share_by_ticker(ticker)
        
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
                'source': 'gRPC'
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

def get_orderbook(ticker="SBER", depth=5):
    """Синхронное получение стакана"""
    client = TinkoffGrpcWorkingClient()
    data = client.get_orderbook_sync(ticker, depth)
    if data:
        client.print_pretty_orderbook(data)
    else:
        print(f"❌ Не удалось получить стакан {ticker}")

def test_connection(ticker="SBER"):
    """Тест подключения"""
    print(f"🧪 Тестируем подключение к Tinkoff для тикера '{ticker}'...")
    try:
        client = TinkoffGrpcWorkingClient()
        instrument = client.find_share_by_ticker(ticker)
        if instrument:
            print(f"✅ Акция найдена!")
            print(f"   Название: {instrument.name}")
            print(f"   Тикер: {instrument.ticker}")
            print(f"   FIGI: {instrument.figi}")
            print(f"   Биржа: {instrument.exchange}")
            print(f"   Класс: {instrument.class_code}")
            print(f"   Лот: {instrument.lot}")
            return True
        else:
            print(f"❌ Акция '{ticker}' не найдена")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def debug_all_shares():
    """Отладка: показывает все доступные акции"""
    print("🔍 Дебаг: получаем список всех акций...")
    try:
        from tinkoff.invest import Client
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        token = os.getenv('INVEST_TOKEN')
        
        with Client(token) as client:
            shares = client.instruments.shares()
            print(f"Всего акций: {len(shares.instruments)}")
            
            print("\nАкции на MOEX в TQBR (первые 20):")
            count = 0
            for share in shares.instruments:
                if share.exchange == 'MOEX' and share.class_code == 'TQBR':
                    print(f"  {share.ticker}: {share.name}")
                    count += 1
                    if count >= 20:
                        break
            
            print(f"\nНайдено акций MOEX TQBR: {count}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# ТОЧКА ВХОДА
# ===========

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("""
📡 Tinkoff gRPC Client (РАБОЧИЙ) - Получение стакана акций MOEX
Использование:
  python scripts/tinkoff_grpc_final.py <команда> [тикер] [глубина]

Команды:
  test [тикер]       - Тест подключения и поиска акции
  get [тикер] [глуб] - Получить стакан (глубина по умолчанию: 5)
  debug              - Показать все доступные акции MOEX
  
Примеры:
  python scripts/tinkoff_grpc_final.py test SBER
  python scripts/tinkoff_grpc_final.py get GAZP 10
  python scripts/tinkoff_grpc_final.py debug
        """)
        return
    
    command = sys.argv[1].lower()
    
    if command == "test":
        ticker = sys.argv[2] if len(sys.argv) > 2 else "SBER"
        test_connection(ticker)
    
    elif command == "get":
        ticker = sys.argv[2] if len(sys.argv) > 2 else "SBER"
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        get_orderbook(ticker, depth)
    
    elif command == "debug":
        debug_all_shares()
    
    else:
        print(f"❌ Неизвестная команда: {command}")

if __name__ == "__main__":
    main()
