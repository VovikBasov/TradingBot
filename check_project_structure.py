import os
import sys

def check_structure():
    print("🔍 Проверяем структуру проекта...")
    
    # Ожидаемая структура из первого сообщения
    expected_dirs = [
        'src',
        'src/data_feed', 
        'src/strategies',
        'src/execution',
        'src/risk_management',
        'src/utils',
        'tests',
        'config',
        'notebooks',
        'scripts',
        'data',
        'logs'
    ]
    
    expected_files = [
        'src/__init__.py',
        'src/data_feed/__init__.py',
        'src/strategies/__init__.py', 
        'src/execution/__init__.py',
        'src/risk_management/__init__.py',
        'src/utils/__init__.py',
        'tests/__init__.py',
        'requirements.txt',
        '.env'
    ]
    
    missing_dirs = []
    missing_files = []
    
    # Проверяем папки
    for dir_path in expected_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
        else:
            print(f"✅ Папка: {dir_path}")
    
    # Проверяем файлы
    for file_path in expected_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✅ Файл: {file_path}")
    
    # Выводим отсутствующие элементы
    if missing_dirs:
        print("\n❌ Отсутствующие папки:")
        for dir_path in missing_dirs:
            print(f"   - {dir_path}")
    
    if missing_files:
        print("\n❌ Отсутствующие файлы:")
        for file_path in missing_files:
            print(f"   - {file_path}")
    
    if not missing_dirs and not missing_files:
        print("\n🎉 Вся структура проекта создана!")
    else:
        print(f"\n📝 Необходимо создать: {len(missing_dirs)} папок, {len(missing_files)} файлов")

if __name__ == "__main__":
    check_structure()
