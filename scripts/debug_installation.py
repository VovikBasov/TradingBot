#!/usr/bin/env python3
"""
Отладка установки Python и пакетов
"""

import sys
from pathlib import Path

# Обновляем путь для импорта после перемещения в scripts/
project_root = Path(__file__).parent.parent  # Поднимаемся на 2 уровня выше
sys.path.insert(0, str(project_root))

print("🔧 Отладка установки Python:")
print(f"Python путь: {sys.executable}")
print(f"Версия Python: {sys.version}")

try:
    import pip
    installed_packages = [p.key for p in pip.get_installed_distributions()]
    print("Установленные пакеты содержащие 'tinkoff':", 
          [p for p in installed_packages if 'tinkoff' in p])
except:
    pass

# Проверим доступные модули
import pkgutil
all_modules = [name for importer, name, ispkg in pkgutil.iter_modules()]
print("Доступные модули:", [m for m in all_modules if 'tinkoff' in m or 'invest' in m])
