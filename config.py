# config.py

# Конфигурация бота
BOT_TOKEN = "YourBotToken"  # Токен бота в BotFather
ADMIN_ID = 123456789        # Telegram ID администратора бота

# Конфигурация панели 3x-UI
PANEL_URL = "URL3X-Ui"      # URL панели 3x-UI с https://...
PANEL_LOGIN = "login"       # Логин от панели 3x-UI
PANEL_PASSWORD = "password" # Пароль от панели 3x-UI

# Тарифы
TARIFFS = {
    "3d":  {"days": 3,  "price": 10, "label": "3 дня • 10 ₽"},
    "30d": {"days": 30, "price": 90, "label": "30 дней • 90 ₽"},
}

# ID инбаундов-заглушек
EXPIRED_INBOUND_IDS = [6, 7] # для истёкших подписок
LIMIT_INBOUND_ID = 9         # для лимита устройств

# Домен для ссылок-подписок
SUB_BASE_URL = "https://boost-vpn.ru"  # Базовый URL для генерации ссылок подписки

# Канал и база данных
CHANNEL_ID = -100000000      # ID телеграм канала
CHANNEL_URL = "https://t.me/telegram" # URL телеграм канала
DB_PATH = "boostvpn.db"
MENU_IMAGE = "menu.jpg"

# Настройки логирования
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"