#!/usr/bin/env python3
"""
Упрощенный запуск бота
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Основная функция"""
    print("🚀 Упрощенный запуск бота...")
    
    # Проверяем окружение
    if not os.path.exists("trading_env/bin/activate"):
        print("❌ Виртуальное окружение не найдено")
        sys.exit(1)
    
    # Проверяем, не запущен ли уже бот
    result = subprocess.run(["pgrep", "-f", "telegram_bot/bot.py"], 
                          capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  Бот уже запущен")
        print("   Запущенные процессы:")
        for pid in result.stdout.strip().split():
            subprocess.run(["ps", "-p", pid, "-o", "pid,etime,command"])
        sys.exit(1)
    
    # Запускаем бота
    print("📡 Запускаем бота...")
    
    # Используем nohup для запуска в фоне
    with open("logs/trading_bot.log", "a") as logfile:
        process = subprocess.Popen(
            [
                "nohup",
                "trading_env/bin/python",
                "telegram_bot/bot.py"
            ],
            stdout=logfile,
            stderr=subprocess.STDOUT
        )
    
    print(f"✅ Бот запущен с PID: {process.pid}")
    print("📝 Логи: tail -f logs/trading_bot.log")
    print("⏹️  Для остановки: ./bot_control.sh stop")

if __name__ == "__main__":
    main()
