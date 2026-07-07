# database.py

import sqlite3
import logging
from datetime import datetime, timedelta
import config
from utils import days_word

log = logging.getLogger(__name__)

def get_db():
    """Возвращает соединение с базой данных."""
    return sqlite3.connect(config.DB_PATH)

def init_db():
    """Инициализирует таблицы в базе данных и выполняет миграции."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            referred_by INTEGER DEFAULT NULL,
            channel_bonus_given INTEGER DEFAULT 0,
            sub_id TEXT DEFAULT NULL,
            xui_client_id TEXT DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            notified_3d INTEGER DEFAULT 0,
            notified_1d INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            tg_id INTEGER PRIMARY KEY,
            expires_at TEXT,
            FOREIGN KEY(tg_id) REFERENCES users(tg_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            days INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            active INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS promocode_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            code TEXT,
            used_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            action TEXT,
            days INTEGER,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(tg_id) REFERENCES users(tg_id)
        )
    """)

    # Миграции для старых баз
    migrations = [
        "ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN channel_bonus_given INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN sub_id TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN xui_client_id TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN notified_3d INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN notified_1d INTEGER DEFAULT 0",
    ]
    for m in migrations:
        try:
            c.execute(m)
            conn.commit()
        except sqlite3.OperationalError:
            pass

    conn.close()
    log.info("База данных готова")

def ensure_user(tg_id: int, username: str = None, referred_by: int = None) -> tuple[bool, int | None]:
    """Создаёт пользователя если не существует. Возвращает (is_new, referred_by)."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT tg_id FROM users WHERE tg_id=?", (tg_id,))
    is_new = not c.fetchone()

    if is_new:
        c.execute(
            "INSERT INTO users (tg_id, username, referred_by) VALUES (?,?,?)",
            (tg_id, username or "", referred_by)
        )
        conn.commit()
        if referred_by and referred_by != tg_id:
            _add_days_internal(referred_by, 7, conn, "Реферальный бонус")
            conn.commit()
    conn.close()
    return is_new, referred_by

def _add_days_internal(tg_id: int, days: int, conn, description: str = "") -> datetime:
    """Внутренняя функция добавления дней (использует переданное соединение)."""
    c = conn.cursor()
    c.execute("SELECT expires_at FROM subscriptions WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    now = datetime.now()

    if row and row[0]:
        try:
            current = datetime.fromisoformat(row[0])
            if current < now:
                current = now
        except Exception:
            current = now
    else:
        current = now

    new_exp = current + timedelta(days=days)

    c.execute(
        "INSERT OR REPLACE INTO subscriptions (tg_id, expires_at) VALUES (?,?)",
        (tg_id, new_exp.isoformat())
    )
    c.execute("UPDATE users SET notified_3d=0, notified_1d=0 WHERE tg_id=?", (tg_id,))
    c.execute(
        "INSERT INTO transactions (tg_id, action, days, description) VALUES (?,?,?,?)",
        (tg_id, "add", days, description)
    )
    return new_exp

def add_days_to_sub(tg_id: int, days: int, description: str = "Покупка подписки") -> datetime:
    conn = get_db()
    new_exp = _add_days_internal(tg_id, days, conn, description)
    conn.commit()
    conn.close()
    return new_exp

def get_subscription(tg_id: int) -> str | None:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT expires_at FROM subscriptions WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def has_active_subscription(tg_id: int) -> bool:
    exp = get_subscription(tg_id)
    if not exp:
        return False
    try:
        return datetime.fromisoformat(exp) > datetime.now()
    except Exception:
        return False

def get_user_sub_id(tg_id: int) -> tuple[str | None, str | None]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT sub_id, xui_client_id FROM users WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)

def set_user_sub_id(tg_id: int, sub_id: str, xui_client_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET sub_id=?, xui_client_id=? WHERE tg_id=?",
        (sub_id, xui_client_id, tg_id)
    )
    conn.commit()
    conn.close()

def get_channel_bonus_given(tg_id: int) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT channel_bonus_given FROM users WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def set_channel_bonus_given(tg_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET channel_bonus_given=1 WHERE tg_id=?", (tg_id,))
    conn.commit()
    conn.close()

def get_referral_count(tg_id: int) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_transactions(tg_id: int, limit: int = 10) -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT action, days, description, created_at FROM transactions "
        "WHERE tg_id=? ORDER BY id DESC LIMIT ?",
        (tg_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return rows

def get_notification_flags(tg_id: int) -> tuple[int, int]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT notified_3d, notified_1d FROM users WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (0, 0)

def set_notification_flag(tg_id: int, flag_name: str):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {flag_name}=1 WHERE tg_id=?", (tg_id,))
    conn.commit()
    conn.close()

def create_promocode(code: str, days: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO promocodes (code, days) VALUES (?,?)", (code.upper(), days))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def delete_promocode(code: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE promocodes SET active=0 WHERE code=?", (code.upper(),))
    conn.commit()
    conn.close()

def get_all_promocodes() -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT code, days, created_at FROM promocodes WHERE active=1 ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def use_promocode(tg_id: int, code: str) -> tuple[bool, int, str]:
    conn = get_db()
    c = conn.cursor()
    code = code.upper().strip()

    c.execute("SELECT days FROM promocodes WHERE code=? AND active=1", (code,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, 0, "❌ Промокод не найден"

    days = row[0]
    c.execute("SELECT id FROM promocode_uses WHERE tg_id=? AND code=?", (tg_id, code))
    if c.fetchone():
        conn.close()
        return False, 0, "⚠️ Промокод уже использован"

    c.execute("INSERT INTO promocode_uses (tg_id, code) VALUES (?,?)", (tg_id, code))
    conn.commit()
    conn.close()

    new_exp = add_days_to_sub(tg_id, days, f"Промокод {code}")
    exp_str = new_exp.strftime("%d.%m.%Y")
    return True, days, f"✅ +{days} {days_word(days)}\nДо {exp_str}"

def get_stats() -> tuple[int, int, int]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM subscriptions WHERE expires_at > datetime('now')")
    active_subs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM promocodes WHERE active=1")
    active_promos = c.fetchone()[0]
    conn.close()
    return total_users, active_subs, active_promos

def get_all_users(limit: int = 25) -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT u.tg_id, u.username, s.expires_at FROM users u "
        "LEFT JOIN subscriptions s ON u.tg_id=s.tg_id "
        "ORDER BY u.created_at DESC LIMIT ?",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return rows
