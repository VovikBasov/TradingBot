import sys
import os

print("🔧 Debug путей Python:")
print(f"Текущая папка: {os.getcwd()}")
print(f"Пути Python:")
for path in sys.path:
    print(f"  - {path}")

print(f"\n📁 Содержимое src/utils/:")
try:
    print(os.listdir("src/utils"))
except Exception as e:
    print(f"Ошибка: {e}")

print(f"\n📁 Содержимое src/data_feed/:")
try:
    print(os.listdir("src/data_feed"))
except Exception as e:
    print(f"Ошибка: {e}")

# Прямой импорт
print(f"\n🔄 Прямой импорт...")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("logger", "src/utils/logger.py")
    logger_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logger_module)
    print("✅ Прямой импорт logger.py - УСПЕХ")
except Exception as e:
    print(f"❌ Прямой импорт logger.py: {e}")
