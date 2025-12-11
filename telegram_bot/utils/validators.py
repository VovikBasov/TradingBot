"""
Валидация ввода пользователя
"""

def validate_ticker(ticker: str) -> bool:
    """
    Простая валидация тикера: только буквы и цифры, длина 2-10
    """
    if not ticker:
        return False
    if len(ticker) < 2 or len(ticker) > 10:
        return False
    if not ticker.isalnum():
        return False
    return True

def validate_depth(depth: int) -> bool:
    """
    Глубина стакана: от 1 до 50
    """
    return 1 <= depth <= 50

def validate_interval(interval: int) -> bool:
    """
    Интервал отправки: от 1 до 3600 секунд
    """
    return 1 <= interval <= 3600
