import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Добавляем путь для импорта utils
current_dir = os.path.dirname(os.path.abspath(__file__))
src_root = os.path.dirname(current_dir)
sys.path.insert(0, src_root)

from tinkoff.invest import Client, GetOrderBookRequest
from tinkoff.invest.schemas import InstrumentStatus
from utils.logger import log

class TinkoffAPIClient:
    """Клиент для работы с Tinkoff Invest API (боевой контур)"""
    
    def __init__(self):
        self.token = os.getenv('INVEST_TOKEN')
        if not self.token:
            log.error("❌ Токен Tinkoff Invest API не найден в .env файле")
            raise ValueError("Токен не найден")
        
        log.info("Tinkoff API клиент инициализирован (БОЕВОЙ КОНТУР)")
    
    def find_instrument_by_ticker(self, ticker):
        """Находит инструмент по тикеру и возвращает его FIGI"""
        with Client(self.token) as client:
            instruments = client.instruments.find_instrument(query=ticker)
            for instrument in instruments.instruments:
                # ИСПРАВЛЕНИЕ: используем instrument.state вместо instrument.instrument_status
                if instrument.ticker == ticker and instrument.state == InstrumentStatus.INSTRUMENT_STATUS_BASE:
                    log.info(f"Найден инструмент: {instrument.name} ({instrument.ticker}), FIGI: {instrument.figi}")
                    return instrument
            log.error(f"Инструмент с тикером {ticker} не найден")
            return None
    
    def get_orderbook(self, ticker: str, depth: int = 5):
        """Получить стакан заявок по тикеру"""
        instrument = self.find_instrument_by_ticker(ticker)
        if not instrument:
            return None
            
        try:
            with Client(self.token) as client:
                request = GetOrderBookRequest(figi=instrument.figi, depth=depth)
                orderbook = client.market_data.get_order_book(request)
                
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
        """Красиво выводим стакан"""
        data = self.get_orderbook(ticker, depth)
        
        if not data:
            print(f"❌ Не удалось получить стакан для {ticker}")
            return
        
        orderbook = data['orderbook']
        instrument = data['instrument']
        
        print(f"\n📊 Стакан по {ticker} ({instrument.name}):")
        print("=" * 60)
        
        # Выводим продажи (asks) - сверху
        if orderbook.asks:
            print("💰 ПРОДАЖИ (asks):")
            for ask in orderbook.asks:
                price = self.quotation_to_float(ask.price)
                quantity = ask.quantity
                print(f"   {price:10.2f} | {quantity:6} лотов")
        
        print("-" * 30)
        
        # Выводим покупки (bids) - снизу  
        if orderbook.bids:
            print("🛒 ПОКУПКИ (bids):")
            for bid in orderbook.bids:
                price = self.quotation_to_float(bid.price)
                quantity = bid.quantity
                print(f"   {price:10.2f} | {quantity:6} лотов")
        
        print("=" * 60)
        if hasattr(orderbook, 'best_bid') and orderbook.best_bid:
            print(f"💎 Лучший спрос: {self.quotation_to_float(orderbook.best_bid):.2f}")
        if hasattr(orderbook, 'best_ask') and orderbook.best_ask:
            print(f"💎 Лучшее предложение: {self.quotation_to_float(orderbook.best_ask):.2f}")
        print(f"⏰ Время: {data['timestamp'].strftime('%H:%M:%S')}")
    
    def quotation_to_float(self, quotation):
        """Конвертируем Quotation в float"""
        if hasattr(quotation, 'units') and hasattr(quotation, 'nano'):
            return quotation.units + quotation.nano / 1e9
        return float(quotation) if quotation else 0.0

if __name__ == "__main__":
    client = TinkoffAPIClient()
    client.print_pretty_orderbook("SBER")
