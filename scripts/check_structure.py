#!/usr/bin/env python3
"""
Проверка структуры проекта торгового бота
"""

import os
import sys
from pathlib import Path

# Обновляем путь для импорта
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_structure():
    print("🔍 Проверяем структуру проекта торгового бота...")
    print("=" * 50)
    
    # Актуальная структура проекта
    expected_dirs = [
        'src',
        'src/data_feed', 
        'src/strategies',
        'src/execution',
        'src/risk_management',
        'src/utils',
        'telegram_bot',
        'telegram_bot/handlers',
        'telegram_bot/services',
        'telegram_bot/utils',
        'tests',
        'scripts',
        'project_utils',
        'logs'
    ]
    
    # Критически важные файлы
    critical_files = [
        'requirements.txt',
        '.env',
        'README.md',
        'manage_bot.py',
        'bot_control.sh',
        
        # Telegram бот
        'telegram_bot/bot.py',
        'telegram_bot/config.py',
        'telegram_bot/get_chat_id.py',
        
        # Ядро системы
        'src/utils/logger.py',
        'src/data_feed/tinkoff_client_simple.py',
        
        # Обработчики
        'telegram_bot/handlers/basic.py',
        'telegram_bot/handlers/orderbook.py',
        'telegram_bot/handlers/settings.py',
        
        # Сервисы
        'telegram_bot/services/tinkoff_service.py',
        'telegram_bot/services/orderbook_service.py'
    ]
    
    # Дополнительные файлы (желательные)
    optional_files = [
        'create_monolithic_export.py',
        'start_bot.py',
        'stop_bot.py',
        'test_bot_monitoring.sh',
        'test_stop_messages.sh',
        'scripts/tinkoff_grpc_client_fixed.py',
        'project_utils/export_project.py'
    ]
    
    missing_dirs = []
    missing_critical_files = []
    missing_optional_files = []
    
    # Проверяем папки
    print("\n📁 Проверка папок:")
    for dir_path in expected_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
            print(f"   ❌ {dir_path}")
        else:
            print(f"   ✅ {dir_path}")
    
    # Проверяем критические файлы
    print("\n📄 Критические файлы:")
    for file_path in critical_files:
        if not os.path.exists(file_path):
            missing_critical_files.append(file_path)
            print(f"   ❌ {file_path}")
        else:
            print(f"   ✅ {file_path}")
    
    # Проверяем дополнительные файлы
    print("\n📄 Дополнительные файлы:")
    for file_path in optional_files:
        if not os.path.exists(file_path):
            missing_optional_files.append(file_path)
            print(f"   ⚠️  {file_path} (отсутствует)")
        else:
            print(f"   ✅ {file_path}")
    
    # Выводим итог
    print("\n" + "=" * 50)
    print("📊 ИТОГ ПРОВЕРКИ:")
    
    if not missing_dirs and not missing_critical_files:
        print("✅ Структура проекта В ПОРЯДКЕ!")
        if missing_optional_files:
            print(f"   ⚠️  Отсутствует {len(missing_optional_files)} дополнительных файлов")
    else:
        if missing_dirs:
            print(f"❌ Отсутствуют папки ({len(missing_dirs)}):")
            for dir_path in missing_dirs:
                print(f"   - {dir_path}")
        
        if missing_critical_files:
            print(f"❌ Отсутствуют критические файлы ({len(missing_critical_files)}):")
            for file_path in missing_critical_files:
                print(f"   - {file_path}")
        
        print("\n🛠 Рекомендации:")
        if '.env' in missing_critical_files:
            print("   - Создайте файл .env из .env.example")
        if 'requirements.txt' in missing_critical_files:
            print("   - Создайте requirements.txt с зависимостями")

if __name__ == "__main__":
    check_structure()
