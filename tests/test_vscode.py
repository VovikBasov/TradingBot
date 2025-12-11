import sys
print("🎯 VSCode тест запущен!")
print(f"Python путь: {sys.executable}")
print(f"Версия Python: {sys.version}")

if "trading_env" in sys.executable:
    print("✅ Работаем в виртуальном окружении!")
else:
    print("❌ НЕ в виртуальном окружении!")

import os
print(f"📁 Путь: {os.getcwd()}")
