#!/usr/bin/env python3
"""
Создаёт монолитный файл со всем кодом проекта
Запуск: python create_monolithic_export.py [путь_к_проекту]
"""

import os
import sys
from pathlib import Path
from datetime import datetime

class MonolithicProjectExporter:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root).resolve()
        self.output_file = None
        self.file_count = 0
        self.total_size = 0
        
        # Папки для исключения (рекурсивно)
        self.exclude_dirs = {
            '.git', '__pycache__', '.pytest_cache', '.mypy_cache',
            'trading_env', 'venv', '.venv', 'env', 'virtualenv',
            'node_modules', '.vscode', '.idea', 'logs', 'data',
            'build', 'dist', '.eggs', '*.egg-info'
        }
        
        # Файлы для исключения
        self.exclude_files = {
            '.DS_Store', 'Thumbs.db', 'desktop.ini',
            '*.pyc', '*.pyo', '*.pyd', '*.so', '*.dll',
            '*.log', '*.tmp', '*.temp', '.coverage',
            '*.db', '*.sqlite', '*.db-journal'
        }
        
        # Расширения файлов, которые мы хотим включить (можно добавлять)
        self.include_extensions = {
            '.py', '.txt', '.md', '.json', '.yaml', '.yml',
            '.toml', '.ini', '.cfg', '.env', '.sh', '.bat',
            '.html', '.css', '.js', '.ts', '.sql', '.csv'
        }
        
    def should_include(self, path: Path) -> bool:
        """Определяем, нужно ли включать файл"""
        # Проверяем папки
        if path.is_dir():
            return path.name not in self.exclude_dirs and not any(
                path.match(pattern) for pattern in self.exclude_dirs if '*' in pattern
            )
        
        # Проверяем файлы
        if any(path.match(pattern) for pattern in self.exclude_files):
            return False
            
        # Проверяем расширения (если есть расширение)
        if path.suffix:
            return path.suffix in self.include_extensions
        
        # Файлы без расширения проверяем по имени
        if path.name in ['.env', '.gitignore', 'Dockerfile', 'docker-compose.yml']:
            return True
            
        return False
    
    def sanitize_content(self, content: str, file_path: Path) -> str:
        """Очищаем чувствительные данные"""
        relative_path = str(file_path.relative_to(self.project_root))
        
        if file_path.name == '.env':
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                if any(keyword in line.upper() for keyword in 
                       ['TOKEN=', 'KEY=', 'SECRET=', 'PASSWORD=', 'API_']):
                    if '=' in line:
                        key = line.split('=')[0].strip()
                        cleaned_lines.append(f"{key}=[SECRET_REMOVED]")
                    else:
                        cleaned_lines.append(line)
                else:
                    cleaned_lines.append(line)
            return '\n'.join(cleaned_lines)
        
        return content
    
    def write_file_header(self, file_path: Path, relative_path: str):
        """Записываем заголовок файла"""
        separator = "=" * 80
        self.output_file.write(f"\n\n{separator}\n")
        self.output_file.write(f"ФАЙЛ: {relative_path}\n")
        self.output_file.write(f"ПОЛНЫЙ ПУТЬ: {file_path}\n")
        self.output_file.write(f"{separator}\n\n")
    
    def process_file(self, file_path: Path):
        """Обрабатываем один файл"""
        try:
            relative_path = str(file_path.relative_to(self.project_root))
            
            # Пишем заголовок
            self.write_file_header(file_path, relative_path)
            
            # Читаем и обрабатываем содержимое
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Очищаем чувствительные данные
                content = self.sanitize_content(content, file_path)
                
                # Записываем содержимое
                self.output_file.write(content)
                
                # Обновляем статистику
                self.file_count += 1
                self.total_size += len(content)
                
                print(f"✅ Добавлен: {relative_path} ({len(content)} байт)")
                
            except UnicodeDecodeError:
                # Пробуем другие кодировки
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                    self.output_file.write(f"# Файл в кодировке latin-1\n{content}")
                    self.file_count += 1
                except:
                    self.output_file.write(f"# Не удалось прочитать файл как текст (бинарный файл)\n")
                    self.output_file.write(f"# Размер: {file_path.stat().st_size} байт\n")
                    
        except Exception as e:
            print(f"⚠️  Ошибка обработки {file_path}: {e}")
    
    def export_project(self, output_filename=None):
        """Основная функция экспорта"""
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = self.project_root / f"PROJECT_FULL_EXPORT_{timestamp}.txt"
        
        print(f"\n🚀 Начинаем монолитный экспорт проекта")
        print(f"📁 Корневая папка: {self.project_root}")
        print(f"💾 Выходной файл: {output_filename}")
        print("=" * 60)
        
        try:
            self.output_file = open(output_filename, 'w', encoding='utf-8')
            
            # Записываем заголовок экспорта
            self.write_export_header()
            
            # Рекурсивно обходим все файлы
            for root, dirs, files in os.walk(self.project_root):
                # Преобразуем root в Path
                root_path = Path(root)
                
                # Фильтруем папки
                dirs[:] = [d for d in dirs if self.should_include(root_path / d)]
                
                # Сортируем для консистентности
                dirs.sort()
                files.sort()
                
                for file in files:
                    file_path = root_path / file
                    if self.should_include(file_path):
                        self.process_file(file_path)
            
            # Записываем статистику
            self.write_statistics()
            
            # Закрываем файл
            self.output_file.close()
            
            print("\n" + "=" * 60)
            print(f"🎉 ЭКСПОРТ ЗАВЕРШЁН!")
            print(f"📊 Файлов экспортировано: {self.file_count}")
            print(f"📦 Общий размер кода: {self.total_size / 1024:.1f} КБ")
            print(f"💾 Итоговый файл: {output_filename}")
            print(f"📏 Размер файла: {output_filename.stat().st_size / 1024 / 1024:.2f} МБ")
            print("=" * 60)
            
            return output_filename
            
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            if self.output_file:
                self.output_file.close()
            return None
    
    def write_export_header(self):
        """Записываем заголовок экспорта"""
        header = f"""
{'=' * 80}
МОНОЛИТНЫЙ ЭКСПОРТ ПРОЕКТА: {self.project_root.name}
{'=' * 80}

📅 Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📁 Корневая папка: {self.project_root}
👤 Экспортёр: MonolithicProjectExporter v1.0

{'=' * 80}
ПРИМЕЧАНИЯ:
1. Файлы разделены заголовками с '======'
2. Чувствительные данные (токены, ключи) заменены на [SECRET_REMOVED]
3. Бинарные файлы пропущены, только их метаданные
4. Все пути указаны относительно корня проекта
{'=' * 80}

"""
        self.output_file.write(header)
    
    def write_statistics(self):
        """Записываем статистику в конец файла"""
        stats = f"""

{'=' * 80}
📊 СТАТИСТИКА ЭКСПОРТА
{'=' * 80}
Всего файлов: {self.file_count}
Общий размер кода: {self.total_size} байт ({self.total_size / 1024:.1f} КБ)
Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 80}

🎯 ИНСТРУКЦИЯ ДЛЯ АНАЛИЗА:
1. Ищите конкретные файлы по строке "ФАЙЛ: "
2. Все пути указаны относительно: {self.project_root}
3. Для навигации используйте поиск по имени файла
4. .env файлы очищены от секретов

{'=' * 80}
КОНЕЦ ЭКСПОРТА
{'=' * 80}
"""
        self.output_file.write(stats)


def main():
    """Точка входа"""
    print("🔧 Monolithic Project Exporter v1.0")
    print("Создаёт единый файл со всем кодом проекта")
    print("=" * 60)
    
    # Определяем путь к проекту
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
        if not os.path.exists(project_path):
            print(f"❌ Путь не существует: {project_path}")
            return
    else:
        project_path = "."
    
    # Создаём экспортёр и запускаем
    exporter = MonolithicProjectExporter(project_path)
    
    # Можно указать конкретное имя файла вторым аргументом
    output_file = None
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    
    result = exporter.export_project(output_file)
    
    if result:
        print(f"\n✅ Экспорт успешно создан: {result}")
        print("\n📋 Быстрые команды для анализа:")
        print(f"   Просмотр: type {result} | more")
        print(f"   Поиск файла: findstr /n \"ФАЙЛ: main.py\" {result}")
        print(f"   Подсчёт строк: find /c /v \"\" {result}")
    else:
        print("❌ Не удалось создать экспорт")

if __name__ == "__main__":
    main()