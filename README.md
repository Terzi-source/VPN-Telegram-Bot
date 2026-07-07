<div align="center">

<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white"/>
<img src="https://img.shields.io/badge/3x--UI-VLESS-orange?style=for-the-badge"/>
<img src="https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>

# VPN Telegram Bot

**A production-ready Telegram bot for automated VPN subscription management,**  
**built on top of the [3x-UI](https://github.com/MHSanaei/3x-ui) panel.**

</div>

---

## Features

| Feature | Description |
|---|---|
| Subscription plans | Configurable periods and prices, easily extended in `config.py` |
| 3x-UI integration | Auto-creates, updates, and removes VLESS clients via the panel REST API |
| Referral system | Users earn **+7 days** for every friend they invite |
| Promo codes | Single-use codes that grant any number of bonus days |
| Smart notifications | Automated reminders at **3 days** and **1 day** before expiry |
| Expiry handling | Background worker moves expired clients to stub inbounds automatically |
| Channel bonus | **+3 days** awarded for joining the Telegram channel |
| Admin panel | Stats, user list, broadcast, manual day grants, promo management |

---

## Architecture

```
vpn-telegram-bot/
│
├── main.py          # Entry point — initializes DB, 3x-UI, bot, and workers
├── config.py        # All configuration: tokens, tariffs, URLs, inbound IDs
│
├── handlers.py      # Telegram command & callback handlers (FSM-based)
├── keyboards.py     # InlineKeyboardMarkup factories
├── texts.py         # Dynamic message text generators
│
├── database.py      # SQLite layer — CRUD, migrations, transactions
├── xui_client.py    # HTTP client for 3x-UI REST API
│
├── workers.py       # Background threads: notifications + expiry check
└── utils.py         # Helpers: Russian pluralization, URL builder, name sanitizer
```

**Data flow:**

```
User action (Telegram)
        │
        ▼
  handlers.py  ──────────►  database.py  (SQLite)
        │
        ▼
  xui_client.py ─────────►  3x-UI panel  (REST API)
        │
        ▼
  workers.py   ──────────►  Scheduled tasks (threading)
```

---

## Setup

### Prerequisites
- Python **3.10+**
- A running [3x-UI](https://github.com/MHSanaei/3x-ui) panel
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### Installation

```bash
git clone https://github.com/Terzi-source/VPN-Telegram-Bot.git
cd VPN-Telegram-Bot
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Open `config.py` and fill in your values:

```python
BOT_TOKEN = "your_bot_token"          # From @BotFather
ADMIN_ID  = 123456789                 # Your Telegram ID

PANEL_URL      = "https://your-panel" # 3x-UI panel URL
PANEL_LOGIN    = "admin"
PANEL_PASSWORD = "password"

CHANNEL_ID  = -100xxxxxxxxxx          # Your Telegram channel ID
CHANNEL_URL = "https://t.me/..."
SUB_BASE_URL = "https://your-domain"  # Base URL for subscription links

EXPIRED_INBOUND_IDS = [6, 7]          # Stub inbound IDs for expired users
LIMIT_INBOUND_ID    = 9
```

### Run

```bash
python main.py
```

---

## How it works

**Subscription purchase**
```
User taps "Buy" → selects plan
    → database extends expiry date
    → xui_client.update_xui_expiry() syncs deadline to all active inbounds
```

**First connection**
```
ensure_user_xui_client()
    → generates UUID client
    → adds it to ALL active inbounds simultaneously
    → stores sub_id + client_uuid in DB
```

**Expiry worker** (every 6 hours)
```
expiry_check_worker()
    → finds users where expires_at <= now
    → removes client from active inbounds
    → moves client to stub inbounds (shows renewal page)
    → sends Telegram notification
```

**Notification worker** (every hour)
```
notification_worker()
    → finds subscriptions expiring in <= 3 days
    → sends push at 3-day threshold  (flag: notified_3d)
    → sends push at 1-day threshold  (flag: notified_1d)
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Telegram API | pyTelegramBotAPI |
| Database | SQLite with auto-migrations |
| VPN panel | 3x-UI (VLESS / XTLS-Reality) |
| Background tasks | Python `threading` |

---

<div align="center">

# Russian

</div>

**Готовый к продакшену Telegram-бот для автоматизированного управления VPN-подписками,**  
**построенный на базе панели [3x-UI](https://github.com/MHSanaei/3x-ui).**

---

## Возможности

| Функция | Описание |
|---|---|
| Тарифные планы | Настраиваемые периоды и цены, легко расширяются в `config.py` |
| Интеграция с 3x-UI | Авто-создание, обновление и удаление VLESS-клиентов через REST API панели |
| Реферальная система | Пользователи получают **+7 дней** за каждого приглашённого друга |
| Промокоды | Одноразовые коды с произвольным количеством бонусных дней |
| Умные уведомления | Автоматические напоминания за **3 дня** и **1 день** до истечения подписки |
| Управление истёкшими | Фоновый воркер автоматически перемещает истёкших клиентов в инбаунды-заглушки |
| Бонус за канал | **+3 дня** за вступление в Telegram-канал |
| Админ-панель | Статистика, список пользователей, рассылка, ручное начисление дней, управление промокодами |

---

## Архитектура

```
vpn-telegram-bot/
│
├── main.py          # Точка входа — инициализация БД, 3x-UI, бота и воркеров
├── config.py        # Вся конфигурация: токены, тарифы, URL, ID инбаундов
│
├── handlers.py      # Обработчики команд и колбэков Telegram (FSM)
├── keyboards.py     # Фабрики InlineKeyboardMarkup
├── texts.py         # Генераторы текстов сообщений
│
├── database.py      # SQLite-слой — CRUD, миграции, транзакции
├── xui_client.py    # HTTP-клиент для REST API 3x-UI
│
├── workers.py       # Фоновые потоки: уведомления и проверка истечения
└── utils.py         # Вспомогательные функции: склонения, URL-builder, санитайзер имён
```

**Поток данных:**

```
Действие пользователя (Telegram)
        │
        ▼
  handlers.py  ──────────►  database.py  (SQLite)
        │
        ▼
  xui_client.py ─────────►  панель 3x-UI  (REST API)
        │
        ▼
  workers.py   ──────────►  Фоновые задачи (threading)
```

---

## Установка

### Требования
- Python **3.10+**
- Запущенная панель [3x-UI](https://github.com/MHSanaei/3x-ui)
- Токен Telegram-бота от [@BotFather](https://t.me/BotFather)

### Установка зависимостей

```bash
git clone https://github.com/Terzi-source/VPN-Telegram-Bot.git
cd VPN-Telegram-Bot
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Конфигурация

Открой `config.py` и заполни свои значения:

```python
BOT_TOKEN = "your_bot_token"          # От @BotFather
ADMIN_ID  = 123456789                 # Твой Telegram ID

PANEL_URL      = "https://your-panel" # URL панели 3x-UI
PANEL_LOGIN    = "admin"
PANEL_PASSWORD = "password"

CHANNEL_ID  = -100xxxxxxxxxx          # ID твоего Telegram-канала
CHANNEL_URL = "https://t.me/..."
SUB_BASE_URL = "https://your-domain"  # Базовый URL для ссылок подписки

EXPIRED_INBOUND_IDS = [6, 7]          # ID инбаундов-заглушек для истёкших пользователей
LIMIT_INBOUND_ID    = 9
```

### Запуск

```bash
python main.py
```

---

## Как работает

**Покупка подписки**
```
Пользователь нажимает "Купить" → выбирает тариф
    → база данных продлевает дату истечения
    → xui_client.update_xui_expiry() синхронизирует дедлайн со всеми активными инбаундами
```

**Первое подключение**
```
ensure_user_xui_client()
    → генерирует UUID клиента
    → добавляет его во ВСЕ активные инбаунды одновременно
    → сохраняет sub_id + client_uuid в БД
```

**Воркер истечения** (каждые 6 часов)
```
expiry_check_worker()
    → находит пользователей, у которых expires_at <= now
    → удаляет клиента из активных инбаундов
    → перемещает клиента в инбаунды-заглушки (показывает страницу продления)
    → отправляет уведомление в Telegram
```

**Воркер уведомлений** (каждый час)
```
notification_worker()
    → находит подписки, истекающие через <= 3 дня
    → отправляет пуш за 3 дня до истечения  (флаг: notified_3d)
    → отправляет пуш за 1 день до истечения  (флаг: notified_1d)
```

---

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.10+ |
| Telegram API | pyTelegramBotAPI |
| База данных | SQLite с авто-миграциями |
| VPN-панель | 3x-UI (VLESS / XTLS-Reality) |
| Фоновые задачи | Python `threading` |

---
