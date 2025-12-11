import os
from dotenv import load_dotenv
load_dotenv()

from tinkoff.invest import Client

token = os.getenv('INVEST_TOKEN')
with Client(token) as client:
    # Тестируем разные варианты вызова
    from tinkoff.invest.schemas import GetOrderBookRequest
    
    # Вариант 1
    try:
        request = GetOrderBookRequest(figi="BBG004730N88", depth=5)
        result = client.market_data.get_order_book(request)
        print("✅ Вариант 1 с GetOrderBookRequest работает")
    except Exception as e:
        print(f"❌ Вариант 1: {e}")
    
    # Вариант 2  
    try:
        result = client.market_data.get_order_book(figi="BBG004730N88", depth=5)
        print("✅ Вариант 2 с прямыми параметрами работает")
    except Exception as e:
        print(f"❌ Вариант 2: {e}")

