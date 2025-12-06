import requests
import pandas as pd
from src.utils.logger import log

class MOEXClient:
    """
    Клиент для работы с API Московской биржи
    """
    
    def __init__(self):
        self.base_url = "https://iss.moex.com/iss"
        self.session = requests.Session()
        log.info("MOEX клиент инициализирован")
    
    def get_security_info(self, ticker: str) -> dict:
        """Получить базовую информацию о бумаге"""
        url = f"{self.base_url}/securities/{ticker}.json"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            log.info(f"Данные по {ticker} получены")
            return data
        except Exception as e:
            log.error(f"Ошибка получения данных по {ticker}: {e}")
            return {}
    
    def get_current_market_data(self, ticker: str) -> dict:
        """Получить текущие рыночные данные"""
        url = f"{self.base_url}/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
        try:
            response = self.session.get(url)
            data = response.json()
            
            # Извлекаем рыночные данные
            market_data = data.get('marketdata', {}).get('data', [])
            if market_data:
                # Базовые поля из рыночных данных
                last_trade = market_data[0]
                return {
                    'last_price': last_trade[12],  # LAST
                    'change': last_trade[13],      # CHANGE
                    'volume': last_trade[9]        # VOLUME
                }
            return {}
        except Exception as e:
            log.error(f"Ошибка получения рыночных данных {ticker}: {e}")
            return {}

if __name__ == "__main__":
    # Тестируем клиент
    client = MOEXClient()
    
    # Тест получения данных по SBER
    sber_info = client.get_security_info("SBER")
    if sber_info:
        log.info("✅ MOEX клиент работает - данные SBER получены")
    
    sber_market = client.get_current_market_data("SBER")
    if sber_market:
        log.info(f"✅ Рыночные данные SBER: {sber_market}")
