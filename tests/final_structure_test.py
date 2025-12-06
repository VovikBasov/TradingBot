import sys
import os

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Тестируем возможность импортировать наши модули"""
    print("🧪 Тестируем импорты...")
    
    try:
        from src.utils.logger import log
        print("✅ src.utils.logger - ОК")
    except ImportError as e:
        print(f"❌ src.utils.logger: {e}")
    
    try:
        from src.data_feed.moex_client import MOEXClient
        print("✅ src.data_feed.moex_client - ОК")
    except ImportError as e:
        print(f"❌ src.data_feed.moex_client: {e}")
    
    try:
        import pandas as pd
        print("✅ pandas - ОК")
    except ImportError as e:
        print(f"❌ pandas: {e}")
    
    print("\n🎯 Тест импортов завершён")

if __name__ == "__main__":
    test_imports()
