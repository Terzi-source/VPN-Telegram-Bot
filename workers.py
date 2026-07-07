# workers.py

import time
import logging
from datetime import datetime, timedelta

import database
import xui_client
import keyboards
from utils import days_word

log = logging.getLogger(__name__)


def notification_worker(bot):
    """Отправляет уведомления за 3 и 1 день до истечения подписки."""
    log.info("Воркер уведомлений запущен")
    while True:
        time.sleep(3600)  # Проверка раз в час
        log.info("Проверка уведомлений...")
        now = datetime.now()

        conn = database.get_db()
        c = conn.cursor()
        c.execute(
            "SELECT u.tg_id, s.expires_at, u.notified_3d, u.notified_1d "
            "FROM users u "
            "JOIN subscriptions s ON u.tg_id=s.tg_id "
            "WHERE s.expires_at > datetime('now')"
        )
        users = c.fetchall()
        conn.close()

        for tg_id, exp_str, notified_3d, notified_1d in users:
            try:
                exp_dt = datetime.fromisoformat(exp_str)
                time_left = exp_dt - now

                # Уведомление за 3 дня
                if timedelta(days=2) < time_left <= timedelta(days=3) and not notified_3d:
                    try:
                        bot.send_message(
                            tg_id,
                            f"⏰ <b>Ваша подписка истекает через 3 дня.</b>\n\n"
                            f"Продлите её, чтобы не потерять доступ.",
                            parse_mode="HTML",
                            reply_markup=keyboards.kb_renew_and_menu()
                        )
                        database.set_notification_flag(tg_id, "notified_3d")
                        log.info(f"Уведомление за 3 дня отправлено пользователю {tg_id}")
                    except Exception as e:
                        log.error(f"Ошибка отправки уведомления (3 дня) для {tg_id}: {e}")

                # Уведомление за 1 день
                elif timedelta(hours=0) < time_left <= timedelta(days=1) and not notified_1d:
                    try:
                        bot.send_message(
                            tg_id,
                            f"🚨 <b>Ваша подписка истекает менее чем через 24 часа!</b>\n\n"
                            f"Продлите её прямо сейчас, чтобы не остаться без доступа.",
                            parse_mode="HTML",
                            reply_markup=keyboards.kb_renew_and_menu()
                        )
                        database.set_notification_flag(tg_id, "notified_1d")
                        log.info(f"Уведомление за 1 день отправлено пользователю {tg_id}")
                    except Exception as e:
                        log.error(f"Ошибка отправки уведомления (1 день) для {tg_id}: {e}")

            except Exception as e:
                log.error(f"Ошибка обработки уведомления для {tg_id}: {e}")

        log.info("Проверка уведомлений завершена")


def expiry_check_worker(bot):
    """Деактивирует клиентов с истёкшей подпиской."""
    log.info("Воркер истёкших подписок запущен")
    while True:
        time.sleep(6 * 3600)  # Проверка каждые 6 часов
        log.info("Проверка истёкших подписок...")
        now_iso = datetime.now().isoformat()

        conn = database.get_db()
        c = conn.cursor()
        # Выбираем пользователей, у которых подписка истекла, но sub_id еще не сброшен
        c.execute(
            "SELECT u.tg_id, u.sub_id, u.xui_client_id "
            "FROM users u "
            "JOIN subscriptions s ON u.tg_id=s.tg_id "
            "WHERE s.expires_at <= ? AND u.xui_client_id IS NOT NULL",
            (now_iso,)
        )
        expired_users = c.fetchall()
        conn.close()

        if not expired_users:
            log.info("Истёкших подписок для обработки не найдено.")
            continue

        all_inbounds_resp = xui_client.xui.get_inbounds()
        if not all_inbounds_resp.get("success") or not all_inbounds_resp.get("obj"):
            log.error("Не удалось получить инбаунды для обработки истёкших подписок.")
            continue

        working_inbounds = xui_client._get_working_inbounds(all_inbounds_resp["obj"])
        working_ids = [ib["id"] for ib in working_inbounds]

        for tg_id, sub_id, client_uuid in expired_users:
            log.info(f"Истекла подписка пользователя {tg_id}")
            if client_uuid:
                # Удаляем из рабочих инбаундов
                for ib_id in working_ids:
                    xui_client.xui.delete_client(ib_id, client_uuid)

                # Добавляем в заглушки
                xui_client.add_to_expired_stubs(tg_id)

                # Сбрасываем xui_client_id в БД, чтобы не обрабатывать повторно
                # sub_id оставляем для истории и возможного продления
                conn = database.get_db()
                c = conn.cursor()
                c.execute("UPDATE users SET xui_client_id = NULL WHERE tg_id = ?", (tg_id,))
                conn.commit()
                conn.close()

            try:
                bot.send_message(
                    tg_id,
                    "⚠️ <b>Ваша подписка истекла</b>\n\nДоступ к VPN-серверам приостановлен. Вы можете продлить подписку в любой момент.",
                    parse_mode="HTML",
                    reply_markup=keyboards.kb_renew_and_menu()
                )
            except Exception as e:
                log.error(f"Не удалось уведомить {tg_id} об истечении подписки: {e}")

        log.info(f"Обработано истёкших подписок: {len(expired_users)}")
