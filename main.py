# main.py

import telebot
import threading
import logging

import config
import database
import xui_client
from handlers import register_handlers
from workers import notification_worker, expiry_check_worker

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format=config.LOG_FORMAT,
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

def main():
    """Главная функция запуска бота."""
    log.info("Запуск BoostVPN Bot...")

    # 1. Инициализация базы данных
    database.init_db()

    # 2. Инициализация и проверка подключения к X-UI
    if xui_client.xui.login():
        log.info("Подключение к 3x-ui успешно")
    else:
        log.critical("Не удалось подключиться к 3x-ui при запуске. Проверьте URL, логин и пароль.")
        # Можно завершить работу, если подключение к панели критично для старта
        # return

    # 3. Инициализация бота
    bot = telebot.TeleBot(config.BOT_TOKEN)

    # 4. Регистрация обработчиков
    register_handlers(bot)

    # 5. Запуск фоновых задач (воркеров)
    threading.Thread(target=notification_worker, args=(bot,), daemon=True).start()
    threading.Thread(target=expiry_check_worker, args=(bot,), daemon=True).start()

    # 6. Запуск long polling
    log.info("Бот запущен и готов к работе")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)


if __name__ == "__main__":
    main()
