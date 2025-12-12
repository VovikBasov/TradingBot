"""
Настройка системы логирования для торгового бота
Поддерживает два вида логов: технические и бизнес-логи
"""

from loguru import logger
import sys
import os
from datetime import datetime
from pathlib import Path

class TradingLogger:
    """Управление логгерами для торгового бота"""
    
    def __init__(self):
        self.logs_dir = Path("logs")
        self.setup_directories()
        self.setup_loggers()
    
    def setup_directories(self):
        """Создаем структуру папок для логов"""
        # Основная папка логов
        self.logs_dir.mkdir(exist_ok=True)
        
        # Подпапки для разных типов логов
        (self.logs_dir / "technical").mkdir(exist_ok=True)
        (self.logs_dir / "business").mkdir(exist_ok=True)
        (self.logs_dir / "errors").mkdir(exist_ok=True)
    
    def setup_loggers(self):
        """Настраиваем все логгеры"""
        
        # Убираем стандартные обработчики
        logger.remove()
        
        # 1. КОНСОЛЬНЫЙ ЛОГГЕР (только важные сообщения)
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            level="INFO",
            colorize=True,
            filter=lambda record: record["level"].name in ["INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        
        # 2. ТЕХНИЧЕСКИЕ ЛОГИ (все DEBUG сообщения)
        logger.add(
            self.logs_dir / "technical" / "technical_{time:YYYY-MM-DD}.log",
            rotation="00:00",  # Новая файл каждый день
            retention="30 days",  # Храним 30 дней
            compression="zip",  # Сжимаем старые логи
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                   "{level: <8} | "
                   "{name}:{function}:{line} | "
                   "{message}",
            level="DEBUG",
            encoding="utf-8"
        )
        
        # 3. БИЗНЕС-ЛОГИ (действия пользователей и системы)
        logger.add(
            self.logs_dir / "business" / "business_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="90 days",  # Бизнес-логи храним дольше
            format="{time:YYYY-MM-DD HH:mm:ss} | "
                   "{extra[component]: <15} | "
                   "{extra[action]: <20} | "
                   "{extra[user_id]: <15} | "
                   "{message}",
            level="INFO",
            encoding="utf-8"
        )
        
        # 4. ЛОГИ ОШИБОК (отдельный файл для критических ошибок)
        logger.add(
            self.logs_dir / "errors" / "errors_{time:YYYY-MM-DD}.log",
            rotation="10 MB",
            retention="60 days",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                   "{level: <8} | "
                   "{name}:{function}:{line} | "
                   "{message}\n"
                   "Traceback: {exception}",
            level="ERROR",
            encoding="utf-8"
        )
        
        # 5. ОБЩИЙ ЛОГ (для совместимости со старым кодом)
        logger.add(
            self.logs_dir / "trading_bot.log",
            rotation="10 MB",
            retention="10 days",
            level="INFO",
            encoding="utf-8"
        )
    
    def business_log(self, component: str, action: str, user_id: str = "system", **kwargs):
        """Запись бизнес-лога
        
        Args:
            component: Компонент системы (bot, api, monitoring)
            action: Действие (start, stop, command, error)
            user_id: ID пользователя или 'system'
            **kwargs: Дополнительные данные
        """
        with logger.contextualize(component=component, action=action, user_id=user_id):
            # Формируем сообщение с дополнительными данными
            details = " | ".join(f"{k}={v}" for k, v in kwargs.items() if v)
            message = details if details else "No details"
            logger.info(message)

# Создаем глобальный экземпляр логгера
log_manager = TradingLogger()
log = logger

# Короткие алиасы для бизнес-логирования
def log_business(component: str, action: str, user_id: str = "system", **kwargs):
    """Короткая функция для бизнес-логирования"""
    log_manager.business_log(component, action, user_id, **kwargs)

def log_command(command: str, user_id: str, **kwargs):
    """Логирование команд пользователя"""
    log_manager.business_log("bot", "command", user_id, command=command, **kwargs)

def log_monitoring(action: str, ticker: str, interval: int = None, **kwargs):
    """Логирование действий мониторинга"""
    log_manager.business_log("monitoring", action, "system", 
                           ticker=ticker, interval=interval, **kwargs)

def log_api_call(service: str, endpoint: str, duration_ms: float = None, **kwargs):
    """Логирование вызовов API"""
    log_manager.business_log("api", "call", "system",
                           service=service, endpoint=endpoint, 
                           duration_ms=duration_ms, **kwargs)

if __name__ == "__main__":
    # Тестируем логгер
    log.info("Технический лог: система логирования запущена")
    log.debug("Отладочное сообщение")
    log.error("Тест ошибки")
    
    # Бизнес-логи
    log_business("bot", "start", "system", version="1.0")
    log_command("/orderbook", "user123", ticker="SBER")
    log_monitoring("start", "SBER", interval=30)
    log_api_call("tinkoff", "get_orderbook", duration_ms=150.5)
