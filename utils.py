# utils.py

import re
import config

def sanitize_name(raw: str) -> str:
    """Убирает технические хвостики из названий инбаундов."""
    return re.sub(r'-\d+[,\d]*[DHMdhm]+[⏳⌛🕐\s]*$', '', raw).strip()

def days_word(n: int) -> str:
    """Склоняет слово 'день' под число."""
    if 11 <= n % 100 <= 19:
        return "дней"
    r = n % 10
    if r == 1:
        return "день"
    if 2 <= r <= 4:
        return "дня"
    return "дней"

def build_sub_url(sub_id: str) -> str:
    return f"{config.SUB_BASE_URL}/sub/{sub_id}"