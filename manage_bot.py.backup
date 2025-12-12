#!/usr/bin/env python3
"""
Единый менеджер бота с защитой от flood control
"""

import os
import sys
import subprocess
import time
from datetime import datetime, timedelta

class BotManager:
    def __init__(self):
        self.last_message_time = {}
        
    def is_bot_running(self):
        """Проверяет, запущен ли бот"""
        result = subprocess.run(['pgrep', '-f', 'telegram_bot/bot.py'], 
                               capture_output=True, text=True)
        return result.returncode == 0
    
    def get_bot_pids(self):
        """Возвращает список PID процессов бота"""
        result = subprocess.run(['pgrep', '-f', 'telegram_bot/bot.py'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split()
        return []
    
    def can_send_message(self, chat_id, min_interval_seconds=5):
        """Проверяет, можно ли отправлять сообщение (защита от flood)"""
        now = datetime.now()
        if chat_id not in self.last_message_time:
            return True
        
        last_time = self.last_message_time[chat_id]
        time_diff = (now - last_time).total_seconds()
        
        return time_diff >= min_interval_seconds
    
    def update_message_time(self, chat_id):
        """Обновляет время последнего сообщения"""
        self.last_message_time[chat_id] = datetime.now()
    
    def start_bot(self):
        """Запускает бота"""
        print("🚀 Запускаем бота...")
        
        if self.is_bot_running():
            print("⚠️  Бот уже запущен")
            print("   Запущенные процессы:", self.get_bot_pids())
            return False
        
        # Запускаем через bot_control.sh
        os.system("./bot_control.sh start")
        
        # Даем боту время на запуск
        time.sleep(3)
        
        if self.is_bot_running():
            print("✅ Бот успешно запущен")
            print("   PID:", self.get_bot_pids())
            return True
        else:
            print("❌ Не удалось запустить бота")
            return False
    
    def stop_bot(self):
        """Останавливает бота"""
        print("⏹️  Останавливаем бота...")
        
        if not self.is_bot_running():
            print("✅ Бот не запущен")
            return True
        
        pids = self.get_bot_pids()
        print(f"📊 Найдено процессов: {len(pids)}")
        
        # Мягкая остановка через bot_control.sh
        os.system("./bot_control.sh stop")
        
        # Ждем завершения
        time.sleep(5)
        
        # Проверяем, остались ли процессы
        remaining_pids = self.get_bot_pids()
        
        if remaining_pids:
            print(f"⚠️  {len(remaining_pids)} процессов не завершились, принудительно останавливаем...")
            for pid in remaining_pids:
                os.system(f"kill -9 {pid} 2>/dev/null")
            time.sleep(1)
        
        if not self.is_bot_running():
            print("✅ Бот успешно остановлен")
            return True
        else:
            print("❌ Не удалось полностью остановить бот")
            return False
    
    def restart_bot(self):
        """Перезапускает бота"""
        print("🔄 Перезапускаем бота...")
        
        if self.is_bot_running():
            self.stop_bot()
            time.sleep(2)
        
        return self.start_bot()
    
    def status(self):
        """Показывает статус бота"""
        print("📊 Статус бота:")
        
        if self.is_bot_running():
            pids = self.get_bot_pids()
            print("✅ Бот запущен")
            print(f"   Процессы: {', '.join(pids)}")
            
            # Показываем информацию о каждом процессе
            for pid in pids:
                result = subprocess.run(['ps', '-p', pid, '-o', 'etime,pid,command'], 
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        print(f"   - {lines[1]}")
        else:
            print("❌ Бот не запущен")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("""
🤖 Менеджер торгового бота

Использование:
  python manage_bot.py <команда>

Команды:
  start     - запустить бота
  stop      - остановить бота
  restart   - перезапустить бота
  status    - показать статус
  stopsoft  - мягкая остановка (без сообщений)
  
Примеры:
  python manage_bot.py start
  python manage_bot.py status
  python manage_bot.py stop
        """)
        return
    
    manager = BotManager()
    command = sys.argv[1].lower()
    
    if command == "start":
        manager.start_bot()
    elif command == "stop":
        manager.stop_bot()
    elif command == "stopsoft":
        # Останавливаем только процессы, без отправки сообщений
        os.system("./stop_bot.py")
    elif command == "restart":
        manager.restart_bot()
    elif command == "status":
        manager.status()
    else:
        print(f"❌ Неизвестная команда: {command}")

if __name__ == "__main__":
    main()
