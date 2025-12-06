print("🔍 Проверяем установку основных библиотек...")

libs_to_check = [
    "pandas", "numpy", "requests", "ccxt", 
    "moexalex", "backtrader", "loguru", "python-dotenv"
]

for lib in libs_to_check:
    try:
        __import__(lib)
        print(f"✅ {lib}")
    except ImportError as e:
        print(f"❌ {lib}: {e}")

print("\n📊 Проверка версий:")
import pandas as pd
import numpy as np
import ccxt

print(f"Pandas: {pd.__version__}")
print(f"Numpy: {np.__version__}")
print(f"CCXT: {ccxt.__version__}")

print("\n🎯 Базовая проверка завершена!")
