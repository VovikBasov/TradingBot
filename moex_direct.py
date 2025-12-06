import requests
import pandas as pd
from loguru import logger

class MOEXClient:
    def __init__(self):
        self.base_url = "https://iss.moex.com/iss"
        self.session = requests.Session()
        logger.info("MOEX клиент инициализирован")
    
    def get_security_info(self, ticker):
        """Получить информацию о бумаге"""
        url = f"{self.base_url}/securities/{ticker}.json"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Данные по {ticker} получены")
            return data
        except Exception as e:
            logger.error(f"Ошибка получения данных по {ticker}: {e}")
            return None
    
    def get_current_price(self, ticker):
        """Получить текущую цену (упрощённо)"""
        url = f"{self.base_url}/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
        try:
            response = self.session.get(url)
            data = response.json()
            # Извлекаем последнюю цену из рыночных данных
            market_data = data['marketdata']['data']
            if market_data:
                last_price = market_data[0][12]  # LAST цена
                return last_price
            return None
        except Exception as e:
            logger.error(f"Ошибка получения цены {ticker}: {e}")
            return None

if __name__ == "__main__":
    client = MOEXClient()
    
    # Тестируем получение данных по SBER
    sber_info = client.get_security_info("SBER")
    if sber_info:
        print("✅ Данные SBER получены")
    
    sber_price = client.get_current_price("SBER")
    if sber_price:
        print(f"✅ Цена SBER: {sber_price}")
