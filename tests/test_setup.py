print("🎉 Виртуальное окружение работает!")
print("Вы в папке:", __file__)

import sys
print("Python путь:", sys.executable)

# Проверим основные библиотеки
try:
    import pandas as pd
    print("✅ pandas установлен")
except ImportError:
    print("❌ pandas НЕ установлен")

try:
    import numpy as np
    print("✅ numpy установлен") 
except ImportError:
    print("❌ numpy НЕ установлен")
