#!/usr/bin/env python3
"""
Простая остановка бота - только завершение процессов
"""

import os
import sys
import subprocess
import time

def main():
    """Основная функция"""
    print("🛑 Останавливаем бота (только завершение процессов)...")
    
    # Ищем процессы бота
    result = subprocess.run(['pgrep', '-f', 'telegram_bot/bot.py'], 
                           capture_output=True, text=True)
    
    if result.returncode != 0:
        print("✅ Бот не запущен")
        return
    
    pids = result.stdout.strip().split()
    print(f"📊 Найдено процессов бота: {len(pids)}")
    
    if not pids:
        print("✅ Бот не запущен")
        return
    
    # Отправляем SIGTERM (мягкое завершение)
    print("🔄 Отправляем сигнал завершения...")
    for pid in pids:
        print(f"  - PID {pid}: отправляем SIGTERM")
        os.system(f"kill -TERM {pid} 2>/dev/null || true")
    
    # Ждем 3 секунды
    time.sleep(3)
    
    # Проверяем, остались ли процессы
    result = subprocess.run(['pgrep', '-f', 'telegram_bot/bot.py'], 
                           capture_output=True, text=True)
    
    if result.returncode == 0:
        pids = result.stdout.strip().split()
        print(f"⚠️  {len(pids)} процессов не завершились, принудительно останавливаем...")
        for pid in pids:
            print(f"  - PID {pid}: отправляем SIGKILL")
            os.system(f"kill -9 {pid} 2>/dev/null || true")
    
    print("✅ Все процессы бота остановлены")

if __name__ == "__main__":
    main()
