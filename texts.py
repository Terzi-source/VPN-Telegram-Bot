# texts.py

from datetime import datetime
import config
import database
import xui_client
from utils import days_word

def text_channel_check() -> str:
    return "<b>Для продолжения подпишитесь на канал</b>"

def text_no_sub_menu() -> str:
    return (
        "🚀 <b>BoostVPN</b>\n\n"
        "<b>Наши преимущества:</b>\n"
        "<blockquote>🏳️ Актуальные обходы блокировок\n"
        "📺 YouTube без рекламы\n"
        "🤖 Доступ ко всем нейросетям\n"
        "🔒 Полная конфиденциальность</blockquote>\n\n"
        "<i>Для подключения оформите подписку</i>\n\n"
        f"<a href='{config.CHANNEL_URL}'>📢 BoostVPN News</a>"
    )

def text_has_sub_menu(tg_id: int) -> str:
    exp = database.get_subscription(tg_id)
    exp_str = "—"
    days_left = 0
    if exp:
        try:
            exp_dt = datetime.fromisoformat(exp)
            exp_str = exp_dt.strftime("%d.%m.%Y")
            days_left = max(0, (exp_dt - datetime.now()).days)
        except Exception:
            pass

    traffic_mb = xui_client.get_traffic_mb(tg_id)
    ref_count = database.get_referral_count(tg_id)

    return (
        f"<b>Главное меню</b>\n\n"
        f"<b>Информация о подписке:</b>\n"
        f"├ Истекает {exp_str}\n"
        f"├ Осталось {days_left} {days_word(days_left)}\n"
        f"├ Использовано трафика {traffic_mb} МБ / ∞\n"
        f"└ Рефералов приглашено {ref_count} (+{ref_count * 7} дн.)\n\n"
        f"<a href='{config.CHANNEL_URL}'>📢 BoostVPN News</a>"
    )
