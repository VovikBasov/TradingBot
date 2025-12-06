import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
src_root = os.path.dirname(current_dir)
sys.path.insert(0, src_root)

from tinkoff.invest import Client
from utils.logger import log

class TinkoffAPIClientSimple:
    def __init__(self):
        self.token = os.getenv('INVEST_TOKEN')
        if not self.token:
            log.error("❌ Токен не найден в .env файле")
            raise ValueError("Токен не найден")
        log.info("Tinkoff API клиент инициализирован (БОЕВОЙ КОНТУР)")
    
    def find_instrument_by_ticker(self, ticker):
        with Client(self.token) as client:
            instruments = client.instruments.find_instrument(query=ticker)
            for instrument in instruments.instruments:
                if instrument.ticker == ticker:
                    log.info(f"Найден инструмент: {instrument.name} ({instrument.ticker}), FIGI: {instrument.figi}")
                    # УБИРАЕМ проблемные атрибуты
                    return instrument
            log.error(f"Инструмент с тикером {ticker} не найден")
            return None
    
    def get_orderbook(self, ticker: str, depth: int = 5):
        instrument = self.find_instrument_by_ticker(ticker)
        if not instrument:
            return None
            
        try:
            with Client(self.token) as client:
                log.info(f"Запрашиваем стакан для FIGI: {instrument.figi}, глубина: {depth}")
                orderbook = client.market_data.get_order_book(figi=instrument.figi, depth=depth)
                
                # Диагностика стакана
                log.info(f"Стакан получен: {orderbook}")
                log.info(f"Количество bids: {len(orderbook.bids)}")
                log.info(f"Количество asks: {len(orderbook.asks)}")
                
                return {
                    'ticker': ticker,
                    'instrument': instrument,
                    'orderbook': orderbook,
                    'timestamp': datetime.now()
                }
                
        except Exception as e:
            log.error(f"Ошибка получения стакана {ticker}: {e}")
            return None
    
    def print_pretty_orderbook(self, ticker: str, depth: int = 5):
        data = self.get_orderbook(ticker, depth)
        
        if not data:
            print(f"❌ Не удалось получить стакан для {ticker}")
            return
        
        orderbook = data['orderbook']
        instrument = data['instrument']
        
        print(f"\n📊 Стакан по {ticker} ({instrument.name}):")
        print("=" * 60)
        
        if orderbook.asks:
            print("💰 ПРОДАЖИ (asks):")
            for ask in orderbook.asks:
                price = self.quotation_to_float(ask.price)
                quantity = ask.quantity
                print(f"   {price:10.2f} | {quantity:6} лотов")
        else:
            print("💰 ПРОДАЖИ (asks): пусто")
        
        print("-" * 30)
        
        if orderbook.bids:
            print("🛒 ПОКУПКИ (bids):")
            for bid in orderbook.bids:
                price = self.quotation_to_float(bid.price)
                quantity = bid.quantity
                print(f"   {price:10.2f} | {quantity:6} лотов")
        else:
            print("🛒 ПОКУПКИ (bids): пусто")
        
        print("=" * 60)
        if hasattr(orderbook, 'best_bid_price') and orderbook.best_bid_price:
            print(f"💎 Лучший спрос: {self.quotation_to_float(orderbook.best_bid_price):.2f}")
        else:
            print(f"💎 Лучший спрос: нет данных")
            
        if hasattr(orderbook, 'best_ask_price') and orderbook.best_ask_price:
            print(f"💎 Лучшее предложение: {self.quotation_to_float(orderbook.best_ask_price):.2f}")
        else:
            print(f"💎 Лучшее предложение: нет данных")
            
        print(f"⏰ Время: {data['timestamp'].strftime('%H:%M:%S')}")
    
    def quotation_to_float(self, quotation):
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0

if __name__ == "__main__":
    client = TinkoffAPIClientSimple()
    client.print_pretty_orderbook("SBER")
