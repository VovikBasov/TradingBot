.PHONY: help setup-telegram get-chat-id run-bot

help:
	@echo "Доступные команды:"
	@echo "  make setup-telegram   - Инструкция по настройке Telegram бота"
	@echo "  make get-chat-id      - Получить Chat ID"
	@echo "  make run-bot          - Проверить настройки бота"

setup-telegram:
	@echo "📱 Настройка Telegram бота:"
	@echo "1. Создайте бота через @BotFather"
	@echo "2. Получите токен"
	@echo "3. Добавьте в .env: TELEGRAM_BOT_TOKEN=ваш_токен"
	@echo "4. Напишите боту сообщение в Телеграме"
	@echo "5. Запустите: make get-chat-id"

get-chat-id:
	@python telegram_bot/get_chat_id.py

run-bot:
	@python telegram_bot/bot.py
