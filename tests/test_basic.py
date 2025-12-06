# test_basic.py
import pandas as pd
import numpy as np
import requests
import ccxt

print("✅ Все основные библиотеки работают!")

# Проверяем данные
data = pd.DataFrame({
    'price': [100, 101, 102, 101, 103],
    'volume': [1000, 1500, 1200, 1800, 2000]
})

print("📊 Тестовые данные:")
print(data)
print(f"📈 Средняя цена: {data['price'].mean():.2f}")

# Проверяем requests
response = requests.get('https://httpbin.org/json')
print(f"🌐 HTTP запрос: {response.status_code}")