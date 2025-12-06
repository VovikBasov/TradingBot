#!/usr/bin/env python3
"""
Скрипт для выгрузки текущего состояния проекта в один файл
Запуск: python project_utils/export_project.py
"""

import os
import json
import base64
from datetime import datetime

def export_project():
    """Экспортирует весь проект в один JSON файл"""
    print("📤 Выгружаем текущее состояние проекта...")
    
    project_data = {
        "export_date": datetime.now().isoformat(),
        "project_name": "Python Trading Bot",
        "files": {}
    }
    
    # Исключаемые папки и файлы
    exclude_dirs = {'.git', '__pycache__', 'trading_env', 'data', 'logs'}
    exclude_files = {'.DS_Store'}
    
    # Собираем все файлы проекта
    for root, dirs, files in os.walk("."):
        # Исключаем системные папки
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file in exclude_files:
                continue
                
            file_path = os.path.join(root, file)
            relative_path = file_path[2:]  # убираем ./
            
            # Пропускаем сам скрипт экспорта
            if "project_utils/export_project.py" in relative_path:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Для .env файла заменяем токен на placeholder
                if file == '.env':
                    lines = content.split('\n')
                    new_lines = []
                    for line in lines:
                        if line.startswith('INVEST_TOKEN='):
                            new_lines.append('INVEST_TOKEN=Введите ваш токен')
                        else:
                            new_lines.append(line)
                    content = '\n'.join(new_lines)
                
                project_data["files"][relative_path] = {
                    "content": content,
                    "size": len(content),
                    "encoding": "utf-8"
                }
                
                print(f"✅ Добавлен: {relative_path}")
                
            except Exception as e:
                print(f"⚠️  Ошибка чтения {relative_path}: {e}")
                project_data["files"][relative_path] = {
                    "content": f"# Ошибка чтения файла: {e}",
                    "size": 0,
                    "error": str(e)
                }
    
    # Сохраняем в файл
    output_filename = f"project_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        
        file_size = os.path.getsize(output_filename) / 1024 / 1024
        print(f"\n🎉 Проект экспортирован в: {output_filename}")
        print(f"📊 Размер файла: {file_size:.2f} MB")
        print(f"📁 Файлов в экспорте: {len(project_data['files'])}")
        print("\n📋 Содержимое проекта:")
        
        # Выводим структуру
        for file_path in sorted(project_data["files"].keys()):
            file_info = project_data["files"][file_path]
            print(f"  - {file_path} ({file_info['size']} байт)")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения экспорта: {e}")
        return False

def main():
    """Основная функция"""
    print("🚀 Trading Bot Project Exporter")
    print("=" * 50)
    print("Экспортирует текущее состояние проекта в один JSON файл")
    print("Токен API заменяется на 'Введите ваш токен'")
    print("=" * 50)
    
    success = export_project()
    
    if success:
        print("\n✅ Экспорт завершен!")
        print("💡 Передайте JSON файл для анализа структуры проекта")
    else:
        print("\n❌ Ошибка при экспорте проекта")

if __name__ == "__main__":
    main()
