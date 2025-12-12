#!/bin/bash

case "$1" in
    start)
        echo "🚀 Запускаем бота..."
        cd /Users/vladimirbasov/Desktop/python_trading
        
        # Проверяем, не запущен ли уже бот
        if pgrep -f "telegram_bot/bot.py" > /dev/null; then
            echo "⚠️  Бот уже запущен"
            $0 status
            exit 1
        fi
        
        # Проверяем виртуальное окружение
        if [ -z "$VIRTUAL_ENV" ]; then
            source trading_env/bin/activate
            echo "✅ Виртуальное окружение активировано"
        fi
        
        # Запускаем бота в фоновом режиме и перенаправляем вывод в лог
        nohup python telegram_bot/bot.py >> logs/trading_bot.log 2>&1 &
        
        # Даем боту время на запуск
        sleep 2
        
        # Проверяем, запустился ли
        if pgrep -f "telegram_bot/bot.py" > /dev/null; then
            BOT_PID=$(pgrep -f "telegram_bot/bot.py" | head -1)
            echo "✅ Бот запущен с PID: $BOT_PID"
            echo "📝 Логи: tail -f logs/trading_bot.log"
        else
            echo "❌ Не удалось запустить бота"
            echo "   Проверьте логи: tail -50 logs/trading_bot.log"
            exit 1
        fi
        ;;
    stop)
        echo "⏹️  Останавливаем бота..."
        
        # Ищем все процессы бота
        PIDS=$(pgrep -f "telegram_bot/bot.py")
        
        if [ -n "$PIDS" ]; then
            # Посылаем SIGTERM (сигнал 15) - мягкое завершение
            echo "🔄 Отправляем сигнал завершения..."
            kill -TERM $PIDS 2>/dev/null
            
            # Ждем 5 секунд для завершения
            sleep 5
            
            # Проверяем, остались ли процессы
            PIDS_LEFT=$(pgrep -f "telegram_bot/bot.py")
            if [ -n "$PIDS_LEFT" ]; then
                echo "⚠️  Некоторые процессы не завершились, принудительно завершаем..."
                kill -9 $PIDS_LEFT 2>/dev/null
            fi
            
            echo "✅ Бот остановлен"
        else
            echo "✅ Бот не был запущен"
        fi
        ;;
    restart)
        echo "🔄 Перезапускаем бота..."
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        echo "📊 Статус бота:"
        PIDS=$(pgrep -f "telegram_bot/bot.py")
        if [ -n "$PIDS" ]; then
            echo "✅ Бот запущен"
            echo "   Процессы: $PIDS"
            for PID in $PIDS; do
                echo "   - PID $PID: $(ps -p $PID -o etime= | xargs) работы"
            done
            echo ""
            echo "   Используйте:"
            echo "     $0 stop   - для остановки"
            echo "     $0 logsf  - для просмотра логов"
        else
            echo "❌ Бот не запущен"
        fi
        ;;
    logs)
        echo "📋 Последние логи бота:"
        if [ -f "logs/trading_bot.log" ]; then
            tail -50 logs/trading_bot.log
        else
            echo "❌ Файл логов не найден"
        fi
        ;;
    logsf)
        echo "📡 Отслеживаем логи в реальном времени:"
        echo "   (Ctrl+C для выхода)"
        echo ""
        if [ -f "logs/trading_bot.log" ]; then
            tail -f logs/trading_bot.log
        else
            echo "❌ Файл логов не найден"
        fi
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|logsf}"
        echo ""
        echo "Команды:"
        echo "  start   - запустить бота"
        echo "  stop    - остановить бота"
        echo "  restart - перезапустить бота"
        echo "  status  - статус бота"
        echo "  logs    - показать последние логи"
        echo "  logsf   - отслеживать логи в реальном времени"
        ;;
esac
