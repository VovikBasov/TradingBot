import requests
import pandas as pd
import sys
import os

# Добавляем путь для импорта utils
current_dir = os.path.dirname(os.path.abspath(__file__))
src_root = os.path.dirname(current_dir)
sys.path.insert(0, src_root)

from utils.logger import log

class MOEXOrderbook:
    """Клиент для получения стакана заявок с MOEX"""
    
    def __init__(self):
        self.base_url = "https://iss.moex.com/iss"
        self.session = requests.Session()
        log.info("MOEX Orderbook клиент инициализирован")
    
    def get_orderbook(self, ticker: str) -> dict:
        """Получить стакан заявок по тикеру"""
        url = f"{self.base_url}/engines/stock/markets/shares/securities/{ticker}/orderbook.json"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Парсим стакан
            orderbook_data = self._parse_orderbook(data)
            log.info(f"Стакан по {ticker} получен")
            return orderbook_data
            
        except Exception as e:
            log.error(f"Ошибка получения стакана {ticker}: {e}")
            log.error(f"URL был: {url}")
            return {}
    
    def _parse_orderbook(self, data: dict) -> dict:
        """Парсим данные стакана"""
        result = {}
        
        # Парсим покупки (bids)
        if 'orderbook' in data and 'bids' in data['orderbook']:
            bids_data = data['orderbook']['bids']
            if bids_data:
                result['bids'] = pd.DataFrame(bids_data)
        
        # Парсим продажи (asks)  
        if 'orderbook' in data and 'asks' in data['orderbook']:
            asks_data = data['orderbook']['asks']
            if asks_data:
                result['asks'] = pd.DataFrame(asks_data)
        
        return result
    
    def print_pretty_orderbook(self, ticker: str, levels: int = 5):
        """Красиво выводим стакан"""
        orderbook = self.get_orderbook(ticker)
        
        if not orderbook or ('bids' not in orderbook and 'asks' not in orderbook):
            print(f"❌ Не удалось получить стакан для {ticker}")
            print("ℹ️  Возможные причины:")
            print("   - Торги по этой бумаге не идут")
            print("   - Проблема с подключением к MOEX")
            print("   - Тикер указан неверно")
            return
        
        print(f"\n📊 Стакан по {ticker}:")
        print("=" * 50)
        
        # Выводим продажи (asks) - сверху
        if 'asks' in orderbook and not orderbook['asks'].empty:
            print("💰 ПРОДАЖИ (asks):")
            asks_df = orderbook['asks'].head(levels)
            for _, row in asks_df.iterrows():
                price = row[0]  # Цена
                quantity = row[1]  # Количество
                print(f"   {price:8.2f} | {quantity:6} лотов")
        
        print("-" * 30)
        
        # Выводим покупки (bids) - снизу
        if 'bids' in orderbook and not orderbook['bids'].empty:
            print("🛒 ПОКУПКИ (bids):")
            bids_df = orderbook['bids'].head(levels)
            for _, row in bids_df.iterrows():
                price = row[0]  # Цена
                quantity = row[1]  # Количество
                print(f"   {price:8.2f} | {quantity:6} лотов")
        
        print("=" * 50)

if __name__ == "__main__":
    client = MOEXOrderbook()
    client.print_pretty_orderbook("SBER")
