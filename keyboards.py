# keyboards.py

from telebot import types
import config

def kb_subscribe():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📢 Подписаться", url=config.CHANNEL_URL))
    kb.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check_sub"))
    return kb

def kb_no_sub_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🛒 Оформить подписку", callback_data="buy_sub"))
    kb.add(types.InlineKeyboardButton("🎫 Промокод", callback_data="promo"))
    kb.add(types.InlineKeyboardButton("👥 Реферальная программа", callback_data="referral"))
    return kb

def kb_has_sub_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔑 Подключение", callback_data="connect"),
        types.InlineKeyboardButton("⚙️ Управление", callback_data="manage_sub"),
    )
    kb.add(types.InlineKeyboardButton("📊 История операций", callback_data="transactions"))
    kb.add(types.InlineKeyboardButton("👥 Реферальная программа", callback_data="referral"))
    return kb

def kb_buy_tariff(back_cb: str = "back_main"):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for key, t in config.TARIFFS.items():
        kb.add(types.InlineKeyboardButton(t["label"], callback_data=f"activate_{key}"))
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data=back_cb))
    return kb

def kb_manage_sub():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🔄 Продлить подписку", callback_data="renew_sub"))
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    return kb

def kb_back(cb: str = "back_main"):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data=cb))
    return kb

def kb_admin_main():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 Статистика", callback_data="adm_stats"),
        types.InlineKeyboardButton("👥 Пользователи", callback_data="adm_users"),
    )
    kb.add(
        types.InlineKeyboardButton("🎫 Промокоды", callback_data="adm_promos"),
        types.InlineKeyboardButton("➕ Промокод", callback_data="adm_create_promo"),
    )
    kb.add(
        types.InlineKeyboardButton("📩 Рассылка", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("🎁 Дать дни", callback_data="adm_give_days"),
    )
    return kb

def kb_admin_back():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 В админ-панель", callback_data="adm_back"))
    return kb

def kb_renew_and_menu():
    """Кнопки для уведомлений — открывают новое сообщение, не редактируют старое."""
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🔄 Продлить подписку", callback_data="open_renew"))
    kb.add(types.InlineKeyboardButton("🏠 В меню", callback_data="open_menu"))
    return kb
