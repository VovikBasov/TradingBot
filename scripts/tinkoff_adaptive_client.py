#!/usr/bin/env python3
"""
Адаптивный Tinkoff клиент - работает с тем, что доступно
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

class TinkoffAdaptiveClient:
    def __init__(self, token=None):
        self.token = token or os.getenv('INVEST_TOKEN')
        if not self.token:
            raise ValueError("Токен не найден")
        log.info("🚀 Инициализация адаптивного клиента")
    
    def find_available_instruments(self):
        """Находит все доступные инструменты"""
        try:
            with Client(self.token) as client:
                # Собираем все доступное
                available = {
                    'shares': [],
                    'bonds': [],
                    'etfs': [],
                    'currencies': []
                }
                
                # Акции
                try:
                    shares = client.instruments.shares()
                    available['shares'] = shares.instruments
                    log.info(f"📈 Акций доступно: {len(shares.instruments)}")
                except Exception as e:
                    log.warning(f"Акции недоступны: {e}")
                
                # Облигации
                try:
                    bonds = client.instruments.bonds()
                    available['bonds'] = bonds.instruments
                    log.info(f"📊 Облигаций доступно: {len(bonds.instruments)}")
                except Exception as e:
                    log.warning(f"Облигации недоступны: {e}")
                
                # ETF
                try:
                    etfs = client.instruments.etfs()
                    available['etfs'] = etfs.instruments
                    log.info(f"📊 ETF доступно: {len(etfs.instruments)}")
                except Exception as e:
                    log.warning(f"ETF недоступны: {e}")
                
                return available
                
        except Exception as e:
            log.error(f"❌ Ошибка получения инструментов: {e}")
            return {}
    
    def find_instrument_by_ticker(self, ticker: str):
        """Умный поиск инструмента по тикеру"""
        try:
            with Client(self.token) as client:
                # Пробуем find_instrument
                found = client.instruments.find_instrument(query=ticker)
                
                if not found.instruments:
                    log.error(f"❌ Инструменты с тикером '{ticker}' не найдены")
                    return None
                
                # Ищем точное совпадение
                for instr in found.instruments:
                    if instr.ticker == ticker:
                        log.info(f"✅ Найден: {instr.name} ({instr.ticker})")
                        log.info(f"   Тип: {instr.instrument_type}")
                        log.info(f"   Биржа: {getattr(instr, 'exchange', 'N/A')}")
                        return instr
                
                log.warning(f"⚠️  Точного совпадения для '{ticker}' нет, берём первый")
                return found.instruments[0]
                
        except Exception as e:
            log.error(f"❌ Ошибка поиска '{ticker}': {e}")
            return None
    
    def get_orderbook(self, ticker: str, depth: int = 5):
        """Получает стакан для любого доступного инструмента"""
        instrument = self.find_instrument_by_ticker(ticker)
        
        if not instrument:
            log.error(f"❌ Не удалось найти '{ticker}'")
            return None
        
        try:
            start_time = datetime.now()
            
            with Client(self.token) as client:
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
        """Печатает стакан"""
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
        
        # Аски
        if orderbook.asks:
            print("💰 ПРОДАЖА:")
            for ask in orderbook.asks[:5]:
                price = self._quotation_to_float(ask.price)
                quantity = ask.quantity
                print(f"  {price:10.2f} | {quantity:6} лотов")
        
        print(f"{'-'*30}")
        
        # Биды
        if orderbook.bids:
            print("🛒 ПОКУПКА:")
            for bid in orderbook.bids[:5]:
                price = self._quotation_to_float(bid.price)
                quantity = bid.quantity
                print(f"  {price:10.2f} | {quantity:6} лотов")
        
        print(f"{'='*60}")
        
        if orderbook.best_bid_price and orderbook.best_ask_price:
            spread = self._quotation_to_float(orderbook.best_ask_price) - self._quotation_to_float(orderbook.best_bid_price)
            print(f"💎 Спрос:   {self._quotation_to_float(orderbook.best_bid_price):.2f}")
            print(f"💎 Предложение: {self._quotation_to_float(orderbook.best_ask_price):.2f}")
            print(f"📏 Спред: {spread:.2f}")
        
        print(f"{'='*60}")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("""
📡 Адаптивный Tinkoff Client
Использование:
  python scripts/tinkoff_adaptive_client.py <команда> [тикер]
  
Команды:
  scan              - Сканировать доступные инструменты
  get <тикер>       - Получить стакан
  test              - Тест с DOMRF
  
Примеры:
  python scripts/tinkoff_adaptive_client.py scan
  python scripts/tinkoff_adaptive_client.py get DOMRF
  python scripts/tinkoff_adaptive_client.py test
        """)
        return
    
    command = sys.argv[1].lower()
    client = TinkoffAdaptiveClient()
    
    if command == "scan":
        instruments = client.find_available_instruments()
        print("\n📋 ДОСТУПНЫЕ ИНСТРУМЕНТЫ:")
        for instr_type, instr_list in instruments.items():
            if instr_list:
                print(f"\n{instr_type.upper()} ({len(instr_list)}):")
                for instr in instr_list[:10]:  # Первые 10
                    print(f"  {instr.ticker}: {instr.name}")
                if len(instr_list) > 10:
                    print(f"  ... и ещё {len(instr_list) - 10}")
    
    elif command == "get":
        ticker = sys.argv[2] if len(sys.argv) > 2 else "DOMRF"
        data = client.get_orderbook(ticker)
        if data:
            client.print_pretty_orderbook(data)
    
    elif command == "test":
        print("🧪 Тест с DOMRF:")
        data = client.get_orderbook("DOMRF")
        if data:
            client.print_pretty_orderbook(data)
            print("✅ Тест пройден! gRPC работает.")
        else:
            print("❌ Тест не пройден")

if __name__ == "__main__":
    main()
