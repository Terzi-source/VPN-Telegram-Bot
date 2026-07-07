# BoostVPN Bot

**[English below](#english)**

---

## Русский

Telegram-бот для управления VPN-подписками на базе панели [3x-UI](https://github.com/MHSanaei/3x-ui).  
Написан на Python с использованием `pyTelegramBotAPI`.

### Возможности

- **Подписки** — тарифные планы с настраиваемыми периодами и ценами
- **Интеграция с 3x-UI** — автоматическое создание/обновление/удаление VLESS-клиентов через REST API панели
- **Реферальная система** — пользователь получает +7 дней за каждого приглашённого друга
- **Промокоды** — одноразовые коды с произвольным количеством бонусных дней
- **Уведомления** — автоматические напоминания за 3 дня и за 1 день до истечения подписки
- **Управление истёкшими подписками** — фоновый воркер перемещает клиентов в инбаунды-заглушки при истечении
- **Бонус за подписку на канал** — +3 дня при подтверждении подписки на Telegram-канал
- **Админ-панель** — статистика, список пользователей, рассылка, ручное начисление дней, управление промокодами

### Стек

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.10+ |
| Telegram API | pyTelegramBotAPI |
| База данных | SQLite (с автомиграциями) |
| VPN-панель | 3x-UI (VLESS/XTLS) |
| Фоновые задачи | `threading` |

### Архитектура

```
boostvpn-bot/
├── main.py          # Точка входа, инициализация и запуск
├── config.py        # Конфигурация (токены, тарифы, URL)
├── handlers.py      # Все обработчики Telegram (команды + callback-кнопки)
├── database.py      # Слой работы с SQLite (CRUD + миграции)
├── xui_client.py    # HTTP-клиент к REST API 3x-UI
├── keyboards.py     # Фабрики InlineKeyboardMarkup
├── texts.py         # Генераторы текстов сообщений
├── workers.py       # Фоновые воркеры (уведомления, истечение)
└── utils.py         # Вспомогательные функции
```

### Установка

```bash
git clone https://github.com/YOUR_USERNAME/boostvpn-bot.git
cd boostvpn-bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Заполните `config.py`:

```python
BOT_TOKEN = "your_bot_token"       # Токен из @BotFather
ADMIN_ID  = 123456789              # Ваш Telegram ID
PANEL_URL = "https://your-panel"   # URL 3x-UI панели
PANEL_LOGIN    = "admin"
PANEL_PASSWORD = "password"
CHANNEL_ID  = -100xxxxxxxxxx       # ID вашего канала
CHANNEL_URL = "https://t.me/..."
SUB_BASE_URL = "https://your-domain"
```

```bash
python main.py
```

### Как это работает

1. Пользователь нажимает «Оформить подписку» → выбирает тариф → в базе данных продлевается дата истечения и вызывается `xui_client.update_xui_expiry()` для обновления срока в панели
2. `ensure_user_xui_client()` при первом подключении создаёт UUID-клиента во всех рабочих инбаундах одновременно
3. Воркер `expiry_check_worker` каждые 6 часов находит пользователей с истёкшей подпиской, удаляет их из рабочих инбаундов и добавляет в инбаунды-заглушки (которые возвращают страницу с предложением продлить)
4. Воркер `notification_worker` каждый час проверяет приближающиеся даты истечения и шлёт push-уведомления

---

## English

A Telegram bot for managing VPN subscriptions powered by the [3x-UI](https://github.com/MHSanaei/3x-ui) panel.  
Built in Python using `pyTelegramBotAPI`.

### Features

- **Subscription plans** — configurable periods and prices
- **3x-UI integration** — automatic VLESS client creation, renewal, and expiry via the panel's REST API
- **Referral system** — users earn +7 days for each invited friend
- **Promo codes** — single-use codes granting custom bonus days
- **Expiry notifications** — automated reminders 3 days and 1 day before subscription ends
- **Expired subscription handling** — background worker moves clients to stub inbounds on expiry
- **Channel subscription bonus** — +3 days for joining the Telegram channel
- **Admin panel** — statistics, user list, broadcast, manual day grants, promo code management

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Telegram API | pyTelegramBotAPI |
| Database | SQLite (with auto-migrations) |
| VPN panel | 3x-UI (VLESS/XTLS) |
| Background tasks | `threading` |

### Architecture

```
boostvpn-bot/
├── main.py          # Entry point — init and launch
├── config.py        # Configuration (tokens, tariffs, URLs)
├── handlers.py      # All Telegram handlers (commands + callbacks)
├── database.py      # SQLite layer (CRUD + migrations)
├── xui_client.py    # HTTP client for 3x-UI REST API
├── keyboards.py     # InlineKeyboardMarkup factories
├── texts.py         # Message text generators
├── workers.py       # Background workers (notifications, expiry)
└── utils.py         # Utility helpers
```

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/boostvpn-bot.git
cd boostvpn-bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Fill in `config.py`:

```python
BOT_TOKEN = "your_bot_token"       # Token from @BotFather
ADMIN_ID  = 123456789              # Your Telegram ID
PANEL_URL = "https://your-panel"   # 3x-UI panel URL
PANEL_LOGIN    = "admin"
PANEL_PASSWORD = "password"
CHANNEL_ID  = -100xxxxxxxxxx       # Your channel ID
CHANNEL_URL = "https://t.me/..."
SUB_BASE_URL = "https://your-domain"
```

```bash
python main.py
```

### How It Works

1. User taps "Buy Subscription" → picks a plan → the expiry date is extended in the database and `xui_client.update_xui_expiry()` is called to sync the deadline to the panel
2. `ensure_user_xui_client()` creates a UUID client across all active inbounds simultaneously on first connection
3. The `expiry_check_worker` runs every 6 hours, finds users with expired subscriptions, removes them from active inbounds, and moves them to stub inbounds (which show a renewal prompt)
4. The `notification_worker` runs every hour, checks upcoming expiry dates, and sends push reminders at 3-day and 1-day thresholds

### License

MIT
