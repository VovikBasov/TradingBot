#!/usr/bin/env python3
"""
Проверка установки основных библиотек для торгового бота
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🔍 Проверяем установку основных библиотек...")
print("=" * 50)

# Библиотеки, критически важные для работы бота
critical_libs = [
    ("grpc", "Базовый gRPC фреймворк (для Tinkoff API)", "grpcio"),
    ("tinkoff.invest", "Официальный Python клиент Tinkoff Invest API", "tinkoff-investments"),
    ("telegram", "Фреймворк для Telegram бота", "python-telegram-bot"),
    ("loguru", "Для логирования", "loguru"),
    ("dotenv", "Для загрузки .env файлов", "python-dotenv"),
    ("aiohttp", "Для асинхронных HTTP запросов", "aiohttp"),
    ("pandas", "Для анализа данных", "pandas"),
    ("numpy", "Для численных операций", "numpy"),
]

print("📦 КРИТИЧЕСКИ ВАЖНЫЕ БИБЛИОТЕКИ:")
print("-" * 40)

all_success = True
for import_name, description, pkg_name in critical_libs:
    try:
        # Для tinkoff.invest требуется особый подход к импорту
        if import_name == "tinkoff.invest":
            from tinkoff.invest import Client
            print(f"✅ {import_name:25} - {description}")
        else:
            __import__(import_name.replace(".", "_"))
            print(f"✅ {import_name:25} - {description}")
    except ImportError as e:
        print(f"❌ {import_name:25} - НЕ НАЙДЕН. Установите: pip install {pkg_name}")
        all_critical_success = False

print("\n📊 ВЕРСИИ УСТАНОВЛЕННЫХ БИБЛИОТЕК:")
print("-" * 40)

try:
    import pandas as pd
    import numpy as np
    import telegram
    import grpc
    import aiohttp
    from tinkoff.invest import __version__ as tinkoff_version

    print(f"Pandas: {pd.__version__}")
    print(f"Numpy: {np.__version__}")
    print(f"Python Telegram Bot: {telegram.__version__}")
    print(f"gRPC (grpcio): {grpc.__version__}")
    print(f"AIOHTTP: {aiohttp.__version__}")
    print(f"Tinkoff Investments: {tinkoff_version}")
except ImportError as e:
    print(f"⚠️ Не удалось проверить некоторые версии: {e}")

print("\n" + "=" * 50)

if all_success:
    print("✅ ОСНОВНЫЕ КОМПОНЕНТЫ УСТАНОВЛЕНЫ.")
    print("   Ядро бота (клиент API, gRPC, телеграм) готово к работе.")
else:
    print("❌ НЕ ВСЕ обязательные библиотеки найдены.")
    print("   Установите недостающие зависимости командой:")
    print("   pip install -r requirements.txt")
