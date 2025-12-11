"""
Форматирование сообщений для Telegram
"""

def format_settings_message(ticker: str, depth: int, interval: int, is_monitoring: bool) -> str:
    """
    Форматирует сообщение с текущими настройками
    """
    status = "🟢 ВКЛ" if is_monitoring else "🔴 ВЫКЛ"
    
    message = (
        f"⚙️ ТЕКУЩИЕ НАСТРОЙКИ:\n\n"
        f"📈 Тикер: {ticker}\n"
        f"📊 Глубина стакана: {depth}\n"
        f"⏱ Интервал отправки: {interval} сек.\n"
        f"📡 Мониторинг: {status}\n"
    )
    return message
