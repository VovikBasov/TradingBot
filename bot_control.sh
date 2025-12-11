#!/bin/bash

case "$1" in
    start)
        echo "🚀 Запускаем бота..."
        cd /Users/vladimirbasov/Desktop/python_trading
        source trading_env/bin/activate
        python telegram_bot/bot.py
        ;;
    stop)
        echo "⏹️  Останавливаем бота..."
        pkill -f "telegram_bot/bot.py"
        ;;
    status)
        echo "📊 Статус бота:"
        if pgrep -f "telegram_bot/bot.py" > /dev/null; then
            echo "✅ Бот запущен"
            ps aux | grep "telegram_bot/bot.py" | grep -v grep
        else
            echo "❌ Бот не запущен"
        fi
        ;;
    logs)
        echo "📋 Логи бота:"
        tail -50 logs/trading_bot.log
        ;;
    *)
        echo "Использование: $0 {start|stop|status|logs}"
        ;;
esac
