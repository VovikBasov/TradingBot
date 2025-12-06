import sys
print("Python путь:", sys.executable)
print("Версия Python:", sys.version)

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
