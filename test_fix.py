import sys
import asyncio
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
async def test():
    from telegram_bot.services.tinkoff_service import TinkoffService
    svc = TinkoffService()
    print("🧪 Тестируем получение стакана для SBER...")
    data = await svc.get_orderbook("SBER", 2)
    if data:
        print(f"✅ Успех! Получено {len(data['bids'])} бидов и {len(data['asks'])} асков.")
        print(f"   Лучшая покупка: {data['best_bid']}, Лучшая продажа: {data['best_ask']}")
    else:
        print("❌ Не удалось получить данные")
asyncio.run(test())
