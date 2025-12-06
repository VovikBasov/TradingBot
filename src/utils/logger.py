from loguru import logger
import sys
import os

def setup_logger():
    """Настройка логгера для trading бота"""
    
    # Создаём папку для логов если её нет
    os.makedirs("logs", exist_ok=True)
    
    # Убираем стандартный handler
    logger.remove()
    
    # Добавляем консольный handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Добавляем файловый handler
    logger.add(
        "logs/trading_bot.log",
        rotation="10 MB",
        retention="10 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    return logger

# Создаём глобальный логгер
log = setup_logger()

if __name__ == "__main__":
    log.info("Логгер настроен корректно!")
    log.debug("Отладочное сообщение")
    log.warning("Предупреждение")
