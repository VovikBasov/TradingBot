#!/bin/bash
echo "=== Тест 1: Остановка через manage_bot.py ==="
python manage_bot.py start
sleep 5
echo "Останавливаем через manage_bot.py stop..."
python manage_bot.py stop
echo ""
sleep 5

echo "=== Тест 2: Ручная остановка (Ctrl+C) ==="
echo "Запустите бота вручную в другом терминале:"
echo "cd ~/Desktop/python_trading && source trading_env/bin/activate && python telegram_bot/bot.py"
echo "Затем нажмите Ctrl+C и проверьте сообщение"
echo ""
echo "=== Тест 3: Остановка через bot_control.sh ==="
python manage_bot.py start
sleep 3
echo "Останавливаем через ./bot_control.sh stop..."
./bot_control.sh stop
sleep 5
python manage_bot.py status
