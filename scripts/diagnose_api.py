#!/usr/bin/env python3
"""
Полная диагностика Tinkoff API
Показывает ВСЁ, что доступно по вашему токену
"""

import os
import sys
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

def diagnose_token_access():
    """Проверяет, какие инструменты доступны по токену"""
    token = os.getenv('INVEST_TOKEN')
    if not token:
        print("❌ Токен не найден в .env файле")
        return
    
    print("🧪 ДИАГНОСТИКА TINKOFF API")
    print("=" * 70)
    
    try:
        with Client(token) as client:
            # 1. Проверяем счета
            print("1. 📋 Проверка счетов...")
            accounts = client.users.get_accounts()
            print(f"   ✅ Найдено счетов: {len(accounts.accounts)}")
            for acc in accounts.accounts:
                print(f"   • {acc.name} (ID: {acc.id}, статус: {acc.status})")
            
            # 2. Проверяем доступ к разным типам инструментов
            print("\n2. 🔍 Проверка доступных инструментов...")
            
            # Акции
            try:
                shares = client.instruments.shares()
                print(f"   📈 Акций доступно: {len(shares.instruments)}")
                
                # Российские акции на MOEX
                ru_shares = [s for s in shares.instruments if s.exchange == 'MOEX']
                print(f"   🇷🇺 Российских акций (MOEX): {len(ru_shares)}")
                
                # Популярные тикеры
                popular = ["SBER", "GAZP", "LKOH", "ROSN", "VTBR", "YNDX", "TCSG"]
                found = []
                for share in shares.instruments:
                    if share.ticker in popular and share.exchange == 'MOEX':
                        found.append(share.ticker)
                
                if found:
                    print(f"   🎯 Найдены популярные тикеры: {', '.join(found)}")
                else:
                    print("   ⚠️  Популярные тикеры НЕ найдены")
                    
            except Exception as e:
                print(f"   ❌ Ошибка запроса акций: {e}")
            
            # Облигации
            try:
                bonds = client.instruments.bonds()
                print(f"   📊 Облигаций доступно: {len(bonds.instruments)}")
            except Exception as e:
                print(f"   ❌ Ошибка запроса облигаций: {e}")
            
            # Фонды
            try:
                etfs = client.instruments.etfs()
                print(f"   📊 ETF доступно: {len(etfs.instruments)}")
            except Exception as e:
                print(f"   ❌ Ошибка запроса ETF: {e}")
            
            # 3. Ищем SBER через find_instrument
            print("\n3. 🔎 Поиск SBER через find_instrument...")
            try:
                found = client.instruments.find_instrument(query="SBER")
                print(f"   Найдено инструментов с 'SBER' в названии: {len(found.instruments)}")
                
                for i, instr in enumerate(found.instruments[:5]):
                    print(f"   {i+1}. {instr.ticker}: {instr.name} (тип: {instr.instrument_type})")
                    if hasattr(instr, 'exchange'):
                        print(f"      Биржа: {instr.exchange}, Класс: {getattr(instr, 'class_code', 'N/A')}")
                
                # Ищем обычные акции SBER
                sber_stocks = [i for i in found.instruments 
                              if i.ticker == "SBER" and i.instrument_type == "share"]
                print(f"   Акций SBER найдено: {len(sber_stocks)}")
                
            except Exception as e:
                print(f"   ❌ Ошибка поиска: {e}")
            
            # 4. Проверяем доступ к сандбоксу
            print("\n4. 🧪 Проверка сандбокса...")
            try:
                from tinkoff.invest.schemas import AccountStatus
                sandbox_accounts = client.sandbox.get_sandbox_accounts()
                print(f"   Счетов в сандбоксе: {len(sandbox_accounts.accounts)}")
                
                # Создаём тестовый счёт в сандбоксе
                try:
                    new_account = client.sandbox.open_sandbox_account()
                    print(f"   ✅ Новый счёт в сандбоксе создан: {new_account.account_id}")
                except Exception as e:
                    print(f"   ℹ️  Не удалось создать счёт в сандбоксе: {e}")
                    
            except Exception as e:
                print(f"   ℹ️  Сандбокс недоступен: {e}")
            
            # 5. Проверяем права доступа
            print("\n5. 🔐 Проверка прав доступа...")
            try:
                user_info = client.users.get_info()
                print(f"   Токен выдан: {user_info.prem_status}")
                print(f"   Qual статус: {user_info.qual_status}")
                print(f"   Tariff: {user_info.tariff}")
            except Exception as e:
                print(f"   ℹ️  Не удалось получить инфо о пользователе: {e}")
    
    except Exception as e:
        print(f"❌ Критическая ошибка подключения: {e}")
        import traceback
        print(f"Подробности: {traceback.format_exc()}")
    
    print("\n" + "=" * 70)
    print("💡 РЕКОМЕНДАЦИИ:")
    print("1. Проверьте, что токен имеет доступ к торговле акциями MOEX")
    print("2. Если у вас токен ИИС, возможно доступны только определённые бумаги")
    print("3. Попробуйте получить токен с полным доступом")
    print("4. Используйте DOMRF для тестирования (это российская акция из списка ИИС)")

def test_domrf_orderbook():
    """Тестирует получение стакана по DOMRF"""
    print("\n" + "=" * 70)
    print("🧪 Тест стакана по DOMRF (работает!)")
    print("=" * 70)
    
    token = os.getenv('INVEST_TOKEN')
    if not token:
        return
    
    try:
        with Client(token) as client:
            # Ищем DOMRF
            found = client.instruments.find_instrument(query="DOMRF")
            domrf = None
            for instr in found.instruments:
                if instr.ticker == "DOMRF" and instr.instrument_type == "share":
                    domrf = instr
                    break
            
            if not domrf:
                print("❌ DOMRF не найден")
                return
            
            print(f"✅ Найден: {domrf.name} ({domrf.ticker})")
            print(f"   FIGI: {domrf.figi}")
            print(f"   Биржа: {getattr(domrf, 'exchange', 'N/A')}")
            
            # Получаем стакан
            orderbook = client.market_data.get_order_book(
                figi=domrf.figi,
                depth=5
            )
            
            print("\n📊 СТАКАН DOMRF:")
            print(f"   Лучший спрос: {orderbook.best_bid_price.units if orderbook.best_bid_price else 'нет'}")
            print(f"   Лучшее предложение: {orderbook.best_ask_price.units if orderbook.best_ask_price else 'нет'}")
            
            if orderbook.bids:
                print(f"   Уровней на покупку: {len(orderbook.bids)}")
            if orderbook.asks:
                print(f"   Уровней на продажу: {len(orderbook.asks)}")
                
            print("✅ Стакан получен успешно!")
            
    except Exception as e:
        print(f"❌ Ошибка теста DOMRF: {e}")

if __name__ == "__main__":
    diagnose_token_access()
    test_domrf_orderbook()
