# handlers.py

import logging
import os
import time
from datetime import datetime
from telebot import types, TeleBot

import config
import database
import xui_client
import keyboards
import texts
from utils import days_word, build_sub_url

log = logging.getLogger(__name__)

# Хранилище состояний для FSM (Finite State Machine)
admin_states = {}
user_states = {}

def check_channel_subscription(bot: TeleBot, tg_id: int) -> bool:
    try:
        member = bot.get_chat_member(config.CHANNEL_ID, tg_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        log.error(f"check_channel_subscription: {e}")
        return False

def send_main_menu(bot: TeleBot, chat_id: int, tg_id: int, message_id: int = None):
    if database.has_active_subscription(tg_id):
        text = texts.text_has_sub_menu(tg_id)
        kb = keyboards.kb_has_sub_menu()
    else:
        text = texts.text_no_sub_menu()
        kb = keyboards.kb_no_sub_menu()

    if message_id:
        try:
            bot.edit_message_caption(
                caption=text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="HTML",
                reply_markup=kb
            )
            return
        except Exception:
            pass

    if os.path.exists(config.MENU_IMAGE):
        try:
            with open(config.MENU_IMAGE, "rb") as photo:
                bot.send_photo(chat_id, photo, caption=text, parse_mode="HTML", reply_markup=kb)
            return
        except Exception as e:
            log.error(f"Ошибка отправки фото меню: {e}")

    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


def register_handlers(bot: TeleBot):
    """Регистрирует все обработчики для бота."""

    @bot.message_handler(commands=["start"])
    def cmd_start(msg):
        args = msg.text.split()
        referred_by = None
        if len(args) > 1 and args[1].startswith("ref"):
            try:
                ref_id = int(args[1][3:])
                if ref_id != msg.from_user.id:
                    referred_by = ref_id
            except (ValueError, IndexError):
                pass

        is_new, referrer = database.ensure_user(msg.from_user.id, msg.from_user.username, referred_by)

        if is_new and referrer:
            try:
                new_exp = database.get_subscription(referrer)
                exp_str = ""
                if new_exp:
                    try:
                        exp_str = f"\nДо {datetime.fromisoformat(new_exp).strftime('%d.%m.%Y')}"
                    except Exception:
                        pass
                bot.send_message(referrer, f"🎉 Новый реферал\n\n+7 дней{exp_str}", parse_mode="HTML")
            except Exception as e:
                log.error(f"Не удалось отправить уведомление рефереру {referrer}: {e}")

        if check_channel_subscription(bot, msg.from_user.id):
            send_main_menu(bot, msg.chat.id, msg.from_user.id)
        else:
            bot.send_message(msg.chat.id, texts.text_channel_check(), parse_mode="HTML", reply_markup=keyboards.kb_subscribe())

    @bot.message_handler(commands=["menu"])
    def cmd_menu(msg):
        database.ensure_user(msg.from_user.id, msg.from_user.username)
        send_main_menu(bot, msg.chat.id, msg.from_user.id)

    @bot.message_handler(commands=["cancel"])
    def cmd_cancel(msg):
        tg_id = msg.from_user.id
        user_states.pop(tg_id, None)
        admin_states.pop(tg_id, None)
        bot.send_message(msg.chat.id, "✅ Действие отменено")

    @bot.message_handler(commands=["admin"])
    def cmd_admin(msg):
        if msg.from_user.id != config.ADMIN_ID:
            bot.send_message(msg.chat.id, "⛔ Нет доступа")
            return
        bot.send_message(msg.chat.id, "🛡 <b>Админ-панель</b>", parse_mode="HTML", reply_markup=keyboards.kb_admin_main())

    @bot.message_handler(func=lambda m: True)
    def handle_text(msg):
        tg_id = msg.from_user.id

        if user_states.get(tg_id) == "wait_promo":
            user_states.pop(tg_id, None)
            success, days, response_text = database.use_promocode(tg_id, msg.text.strip())
            kb = types.InlineKeyboardMarkup(row_width=1)
            if success:
                kb.add(types.InlineKeyboardButton("🔑 Подключиться", callback_data="connect"))
            kb.add(types.InlineKeyboardButton("🏠 Меню", callback_data="open_menu"))
            bot.send_message(msg.chat.id, response_text, parse_mode="HTML", reply_markup=kb)
            return

        if tg_id != config.ADMIN_ID:
            return

        if admin_states.get(tg_id) == "adm_promo_code":
            admin_states[tg_id] = {"step": "adm_promo_days", "code": msg.text.strip()}
            bot.send_message(
                msg.chat.id,
                f"Промокод: <code>{msg.text.strip().upper()}</code>\n\nВведите количество дней:",
                parse_mode="HTML"
            )
            return

        if isinstance(admin_states.get(tg_id), dict) and admin_states[tg_id].get("step") == "adm_promo_days":
            try:
                days = int(msg.text.strip())
                code = admin_states.pop(tg_id)["code"]
                if database.create_promocode(code, days):
                    bot.send_message(
                        msg.chat.id,
                        f"✅ Промокод создан\n\n<code>{code.upper()}</code> — {days} {days_word(days)}",
                        parse_mode="HTML",
                        reply_markup=keyboards.kb_admin_main()
                    )
                else:
                    bot.send_message(msg.chat.id, "❌ Такой промокод уже существует", reply_markup=keyboards.kb_admin_main())
            except ValueError:
                bot.send_message(msg.chat.id, "❌ Введите число")
            return

        if admin_states.get(tg_id) == "adm_del_promo":
            admin_states.pop(tg_id, None)
            code = msg.text.strip().upper()
            database.delete_promocode(code)
            bot.send_message(
                msg.chat.id,
                f"🗑 Промокод <code>{code}</code> деактивирован",
                parse_mode="HTML",
                reply_markup=keyboards.kb_admin_main()
            )
            return

        if admin_states.get(tg_id) == "adm_broadcast":
            admin_states.pop(tg_id, None)
            all_ids = [user[0] for user in database.get_all_users(limit=1000000)] # Get all users
            ok, fail = 0, 0
            for uid in all_ids:
                try:
                    bot.send_message(uid, msg.text, parse_mode="HTML")
                    ok += 1
                    time.sleep(0.05)
                except Exception:
                    fail += 1
            bot.send_message(
                msg.chat.id,
                f"📩 Рассылка завершена\n\n✅ Доставлено: {ok}\n❌ Ошибок: {fail}",
                parse_mode="HTML",
                reply_markup=keyboards.kb_admin_main()
            )
            return

        if admin_states.get(tg_id) == "adm_give_id":
            try:
                target_id = int(msg.text.strip())
                admin_states[tg_id] = {"step": "adm_give_days", "target_id": target_id}
                bot.send_message(
                    msg.chat.id,
                    f"ID: <code>{target_id}</code>\n\nСколько дней начислить?",
                    parse_mode="HTML"
                )
            except ValueError:
                bot.send_message(msg.chat.id, "❌ Введите числовой ID")
            return

        if isinstance(admin_states.get(tg_id), dict) and admin_states[tg_id].get("step") == "adm_give_days":
            try:
                days = int(msg.text.strip())
                target_id = admin_states.pop(tg_id)["target_id"]
                database.ensure_user(target_id)
                new_exp = database.add_days_to_sub(target_id, days, "Начисление администратором")
                exp_str = new_exp.strftime("%d.%m.%Y")
                bot.send_message(
                    msg.chat.id,
                    f"✅ Готово\n\nID: <code>{target_id}</code>\n+{days} {days_word(days)}\nДо {exp_str}",
                    parse_mode="HTML",
                    reply_markup=keyboards.kb_admin_main()
                )
                try:
                    bot.send_message(target_id, f"🎁 Вам начислено {days} {days_word(days)}\nДо {exp_str}", parse_mode="HTML")
                except Exception:
                    pass
            except ValueError:
                bot.send_message(msg.chat.id, "❌ Введите число")
            return

    @bot.callback_query_handler(func=lambda c: True)
    def handle_callback(call):
        tg_id = call.from_user.id
        database.ensure_user(tg_id, call.from_user.username)
        data = call.data

        if data == "open_menu":
            bot.answer_callback_query(call.id)
            send_main_menu(bot, call.message.chat.id, tg_id)
            return

        if data == "open_renew":
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "⚡️ <b>Продление подписки</b>\n\nВыберите период:",
                parse_mode="HTML",
                reply_markup=keyboards.kb_buy_tariff("open_menu")
            )
            return

        if data == "check_sub":
            if check_channel_subscription(bot, tg_id):
                if not database.get_channel_bonus_given(tg_id):
                    database.set_channel_bonus_given(tg_id)
                    new_exp = database.add_days_to_sub(tg_id, 3, "Бонус за подписку на канал")
                    exp_str = new_exp.strftime("%d.%m.%Y")
                    bot.answer_callback_query(call.id, f"✅ Бонус начислен до {exp_str}!", show_alert=True)
                else:
                    bot.answer_callback_query(call.id, "✅ Подтверждено", show_alert=False)
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
                send_main_menu(bot, call.message.chat.id, tg_id)
            else:
                bot.answer_callback_query(call.id, "❌ Вы ещё не подписались на канал", show_alert=True)
            return

        if data == "back_main":
            send_main_menu(bot, call.message.chat.id, tg_id, call.message.message_id)
            bot.answer_callback_query(call.id)
            return

        elif data == "buy_sub":
            bot.edit_message_caption(
                caption="⚡️ <b>Тарифы BoostVPN</b>\n\nВыберите период:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_buy_tariff("back_main")
            )

        elif data.startswith("activate_"):
            tariff_key = data.split("activate_")[1]
            tariff = config.TARIFFS.get(tariff_key)
            if not tariff:
                bot.answer_callback_query(call.id, "❌ Неизвестный тариф")
                return
            new_exp = database.add_days_to_sub(tg_id, tariff["days"], f"Покупка: {tariff['label']}")
            exp_str = new_exp.strftime("%d.%m.%Y")
            bot.answer_callback_query(call.id, f"✅ Подписка активна до {exp_str}", show_alert=True)
            send_main_menu(bot, call.message.chat.id, tg_id, call.message.message_id)

        elif data == "manage_sub":
            bot.edit_message_caption(
                caption="⚙️ <b>Управление подпиской</b>\n\n<i>Здесь вы можете продлить или проверить статус подписки</i>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_manage_sub()
            )

        elif data == "renew_sub":
            bot.edit_message_caption(
                caption="⚡️ <b>Продление подписки</b>\n\nВыберите период:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_buy_tariff("manage_sub")
            )

        elif data == "connect":
            if not database.has_active_subscription(tg_id):
                bot.answer_callback_query(call.id, "❌ Нет активной подписки", show_alert=True)
                return

            bot.answer_callback_query(call.id, "⏳ Получаем ссылку...")

            sub_id = xui_client.ensure_user_xui_client(tg_id)
            if not sub_id:
                bot.edit_message_caption(
                    caption="❌ Не удалось получить ссылку\n\nПопробуйте позже или напишите в поддержку",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=keyboards.kb_back("back_main")
                )
                return

            sub_url = build_sub_url(sub_id)
            exp = database.get_subscription(tg_id)
            exp_str = "—"
            if exp:
                try:
                    exp_str = datetime.fromisoformat(exp).strftime("%d.%m.%Y")
                except Exception:
                    pass

            bot.edit_message_caption(
                caption=(
                    f"🔑 <b>Подключение к VPN</b>\n\n"
                    f"📅 Подписка активна до {exp_str}\n\n"
                    f"<b>Ваша ссылка-подписка:</b>\n"
                    f"<code>{sub_url}</code>\n\n"
                    f"<b>Как подключиться:</b>\n"
                    f"<blockquote>"
                    f"• Скачайте приложение (кнопки ниже)\n"
                    f"• Скопируйте ссылку выше\n"
                    f"• В приложении: добавить подписку → вставить ссылку"
                    f"</blockquote>"
                ),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_back("back_main")
            )

        elif data == "promo":
            user_states[tg_id] = "wait_promo"
            bot.edit_message_caption(
                caption="🎫 <b>Активация промокода</b>\n\nВведите промокод:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_back("back_main")
            )

        elif data == "transactions":
            transactions = database.get_transactions(tg_id, 10)
            if not transactions:
                text = "📊 <b>История операций</b>\n\nПока пусто"
            else:
                text = "📊 <b>История операций</b>\n\n"
                for action, days, desc, created in transactions:
                    try:
                        dt = datetime.fromisoformat(created).strftime("%d.%m %H:%M")
                    except Exception:
                        dt = "—"
                    sign = "+" if action == "add" else "-"
                    text += f"{dt} • {sign}{days} дн. • {desc}\n"

            bot.edit_message_caption(
                caption=text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_back("back_main")
            )

        elif data == "referral":
            ref_count = database.get_referral_count(tg_id)
            ref_link = f"https://t.me/{bot.get_me().username}?start=ref{tg_id}"
            bot.edit_message_caption(
                caption=(
                    f"👥 <b>Реферальная программа</b>\n\n"
                    f"<i>Приглашайте друзей и получайте +7 дней за каждого</i>\n\n"
                    f"<b>Приглашено:</b> {ref_count} чел.\n"
                    f"<b>Заработано:</b> {ref_count * 7} дней\n\n"
                    f"<b>📎 Ваша ссылка:</b>\n"
                    f"<code>{ref_link}</code>"
                ),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_back("back_main")
            )

        # Admin Callbacks
        elif data == "adm_stats" and tg_id == config.ADMIN_ID:
            total_users, active_subs, active_promos = database.get_stats()
            bot.edit_message_text(
                f"📊 <b>Статистика</b>\n\n"
                f"👥 Всего пользователей: {total_users}\n"
                f"✅ Активных подписок: {active_subs}\n"
                f"🎫 Активных промокодов: {active_promos}",
                call.message.chat.id, call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_admin_back()
            )

        elif data == "adm_users" and tg_id == config.ADMIN_ID:
            users = database.get_all_users(25)
            text = "👥 <b>Последние 25 пользователей</b>\n\n"
            for uid, uname, exp in users:
                if exp:
                    try:
                        is_active = datetime.fromisoformat(exp) > datetime.now()
                        exp_str = datetime.fromisoformat(exp).strftime("%d.%m")
                        icon = "✅" if is_active else "❌"
                    except Exception:
                        icon, exp_str = "❓", "—"
                else:
                    icon, exp_str = "❌", "нет"
                text += f"{icon} <code>{uid}</code> @{uname or '—'} до {exp_str}\n"
            bot.edit_message_text(
                text, call.message.chat.id, call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_admin_back()
            )

        elif data == "adm_promos" and tg_id == config.ADMIN_ID:
            promos = database.get_all_promocodes()
            text = f"🎫 <b>Промокоды ({len(promos)})</b>\n\n" if promos else "🎫 <b>Промокоды</b>\n\nПусто"
            for code, d, _ in promos:
                text += f"• <code>{code}</code> — {d} {days_word(d)}\n"
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.add(types.InlineKeyboardButton("➕ Создать", callback_data="adm_create_promo"))
            kb.add(types.InlineKeyboardButton("🗑 Удалить", callback_data="adm_del_promo"))
            kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="adm_back"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)

        elif data == "adm_create_promo" and tg_id == config.ADMIN_ID:
            admin_states[tg_id] = "adm_promo_code"
            bot.edit_message_text(
                "✏️ <b>Создание промокода</b>\n\nВведите название промокода:",
                call.message.chat.id, call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_admin_back()
            )

        elif data == "adm_del_promo" and tg_id == config.ADMIN_ID:
            promos = database.get_all_promocodes()
            if not promos:
                bot.answer_callback_query(call.id, "Нет активных промокодов", show_alert=True)
                return
            admin_states[tg_id] = "adm_del_promo"
            text = "🗑 <b>Удаление промокода</b>\n\nВведите код:\n\n"
            for code, d, _ in promos:
                text += f"• <code>{code}</code>\n"
            bot.edit_message_text(
                text, call.message.chat.id, call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_admin_back()
            )

        elif data == "adm_broadcast" and tg_id == config.ADMIN_ID:
            admin_states[tg_id] = "adm_broadcast"
            conn = database.get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            total = c.fetchone()[0]
            conn.close()
            bot.edit_message_text(
                f"📩 <b>Рассылка</b>\n\nПолучателей: {total}\n\nВведите текст сообщения:",
                call.message.chat.id, call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_admin_back()
            )

        elif data == "adm_give_days" and tg_id == config.ADMIN_ID:
            admin_states[tg_id] = "adm_give_id"
            bot.edit_message_text(
                "🎁 <b>Начисление дней</b>\n\nВведите Telegram ID пользователя:",
                call.message.chat.id, call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_admin_back()
            )

        elif data == "adm_back" and tg_id == config.ADMIN_ID:
            admin_states.pop(tg_id, None)
            bot.edit_message_text(
                "🛡 <b>Админ-панель</b>",
                call.message.chat.id, call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboards.kb_admin_main()
            )

        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass