#!/usr/bin/env python3
"""
Простой тест Tinkoff API (боевой контур)
"""

import os
import sys
from dotenv import load_dotenv

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

load_dotenv()

def main():
    print("🧪 Тестируем подключение к Tinkoff API...")
    
    token = os.getenv('INVEST_TOKEN')
    if not token:
        print("❌ Токен не найден в .env файле")
        return
    
    try:
        from tinkoff.invest import Client
        
        with Client(token) as client:
            # Проверяем доступные счета
            accounts = client.users.get_accounts()
            print("✅ Подключение успешно!")
            print(f"📋 Найдено счетов: {len(accounts.accounts)}")
            
            for account in accounts.accounts:
                print(f"   - {account.name} (ID: {account.id})")
                
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

if __name__ == "__main__":
    main()
