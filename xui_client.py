# xui_client.py

import requests
import json
import uuid
import logging
from datetime import datetime, timedelta

import config
import database
from utils import sanitize_name, build_sub_url

log = logging.getLogger(__name__)

class XUIClient:
    def __init__(self):
        self.base = config.PANEL_URL
        self.session = requests.Session()
        self.cookie = None

    def login(self) -> bool:
        try:
            r = self.session.post(
                f"{self.base}/login",
                json={"username": config.PANEL_LOGIN, "password": config.PANEL_PASSWORD},
                timeout=10
            )
            data = r.json()
            if data.get("success"):
                self.cookie = r.cookies
                log.info("3x-ui: авторизация успешна")
                return True
            log.error(f"3x-ui: ошибка авторизации: {data}")
            return False
        except Exception as e:
            log.error(f"3x-ui login: {e}")
            return False

    def _req(self, method: str, path: str, **kwargs) -> dict:
        if not self.cookie:
            if not self.login():
                return {"success": False, "msg": "Login failed"}
        try:
            url = f"{self.base}/panel/api/inbounds{path}"
            r = self.session.request(method, url, cookies=self.cookie, timeout=15, **kwargs)
            if r.status_code == 401: # Unauthorized
                log.info("3x-ui: сессия истекла, переподключение...")
                if not self.login():
                    return {"success": False, "msg": "Re-login failed"}
                r = self.session.request(method, url, cookies=self.cookie, timeout=15, **kwargs)
            return r.json()
        except requests.exceptions.RequestException as e:
            log.error(f"3x-ui request error: {e}")
            return {"success": False, "msg": str(e)}
        except json.JSONDecodeError as e:
            log.error(f"3x-ui JSON decode error: {e}, Response: {r.text}")
            return {"success": False, "msg": "JSON decode error"}

    def get_inbounds(self) -> dict:
        return self._req("GET", "/list")

    def add_client(self, inbound_id: int, client_data: dict) -> dict:
        payload = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client_data]})
        }
        return self._req("POST", "/addClient", json=payload)

    def update_client(self, inbound_id: int, client_id: str, client_data: dict) -> dict:
        payload = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client_data]})
        }
        return self._req("POST", f"/updateClient/{client_id}", json=payload)

    def delete_client(self, inbound_id: int, client_id: str) -> dict:
        return self._req("POST", f"/{inbound_id}/delClient/{client_id}")

    def get_client_traffics(self, email: str) -> dict:
        return self._req("GET", f"/getClientTraffics/{email}")

# Глобальный экземпляр клиента
xui = XUIClient()

# XUI хелперы

def get_traffic_mb(tg_id: int) -> float:
    sub_id, _ = database.get_user_sub_id(tg_id)
    if not sub_id:
        return 0.0
    try:
        res = xui.get_client_traffics(sub_id)
        if res.get("success") and res.get("obj"):
            obj = res["obj"]
            total = obj.get("up", 0) + obj.get("down", 0)
            return round(total / (1024 * 1024), 1)
    except Exception:
        pass
    return 0.0

def _get_working_inbounds(all_inbounds: list) -> list:
    """Возвращает только рабочие инбаунды (без заглушек)."""
    return [
        ib for ib in all_inbounds
        if ib["id"] not in config.EXPIRED_INBOUND_IDS and ib["id"] != config.LIMIT_INBOUND_ID
    ]

def _get_client_flow(inbound: dict) -> str:
    """Вытаскивает flow из настроек инбаунда."""
    try:
        settings = json.loads(inbound.get("settings") or "{}")
        clients = settings.get("clients", [])
        return clients[0].get("flow", "") if clients else ""
    except Exception:
        return ""

def _make_client_data(client_uuid: str, sub_id: str, inbound_id: int,
                      tg_id: int = 0, flow: str = "", expiry_ms: int = 0) -> dict:
    """Формирует объект клиента для 3x-ui."""
    return {
        "id": client_uuid,
        "flow": flow,
        "email": f"{sub_id}_{inbound_id}",
        "limitIp": 0,
        "totalGB": 0,
        "expiryTime": expiry_ms,
        "enable": True,
        "tgId": str(tg_id) if tg_id else "",
        "subId": sub_id,
        "reset": 0
    }

def ensure_user_xui_client(tg_id: int) -> str | None:
    """Создаёт XUI-клиента если ещё нет. Возвращает sub_id."""
    sub_id, xui_client_id = database.get_user_sub_id(tg_id)
    if sub_id:
        return sub_id

    all_inbounds_resp = xui.get_inbounds()
    if not all_inbounds_resp.get("success") or not all_inbounds_resp.get("obj"):
        log.error("ensure_user_xui_client: не удалось получить инбаунды")
        return None

    client_uuid = str(uuid.uuid4())
    sub_id = uuid.uuid4().hex[:16]

    working = _get_working_inbounds(all_inbounds_resp["obj"])
    success_count = 0

    for ib in working:
        ib_id = ib["id"]
        raw_remark = ib.get("remark", "")
        clean_remark = sanitize_name(raw_remark)
        if clean_remark != raw_remark:
            log.info(f"Инбаунд {ib_id}: '{raw_remark}' → '{clean_remark}'")

        client_data = _make_client_data(
            client_uuid, sub_id, ib_id,
            tg_id=tg_id,
            flow=_get_client_flow(ib),
            expiry_ms=0  # управляем через БД
        )
        result = xui.add_client(ib_id, client_data)
        if result.get("success"):
            success_count += 1
            log.info(f"Клиент добавлен в inbound {ib_id} ({clean_remark})")
        else:
            log.error(f"Ошибка добавления в inbound {ib_id}: {result.get('msg')}")

    if success_count > 0:
        database.set_user_sub_id(tg_id, sub_id, client_uuid)
        log.info(f"XUI клиент создан для {tg_id}: sub_id={sub_id}")
        return sub_id

    log.error(f"Не удалось создать XUI клиента для {tg_id}")
    return None

def update_xui_expiry(tg_id: int, new_exp: datetime):
    """Обновляет дату истечения клиента во всех рабочих инбаундах."""
    sub_id, client_uuid = database.get_user_sub_id(tg_id)
    if not sub_id or not client_uuid:
        return

    all_inbounds_resp = xui.get_inbounds()
    if not all_inbounds_resp.get("success") or not all_inbounds_resp.get("obj"):
        return

    expiry_ms = int(new_exp.timestamp() * 1000)
    working = _get_working_inbounds(all_inbounds_resp["obj"])

    for ib in working:
        ib_id = ib["id"]
        client_data = _make_client_data(
            client_uuid, sub_id, ib_id,
            tg_id=tg_id,
            flow=_get_client_flow(ib),
            expiry_ms=expiry_ms
        )
        res = xui.update_client(ib_id, client_uuid, client_data)
        if not res.get("success"):
            xui.add_client(ib_id, client_data)

def add_to_expired_stubs(tg_id: int):
    """Добавляет клиента в инбаунды-заглушки истёкших подписок."""
    sub_id, client_uuid = database.get_user_sub_id(tg_id)
    if not sub_id or not client_uuid:
        return

    all_inbounds_resp = xui.get_inbounds()
    if not all_inbounds_resp.get("success") or not all_inbounds_resp.get("obj"):
        return

    ib_map = {ib["id"]: ib for ib in all_inbounds_resp["obj"]}
    for stub_id in config.EXPIRED_INBOUND_IDS:
        ib = ib_map.get(stub_id)
        if not ib:
            continue
        client_data = _make_client_data(
            client_uuid, sub_id, stub_id,
            flow=_get_client_flow(ib)
        )
        xui.add_client(stub_id, client_data)

def remove_from_expired_stubs(tg_id: int):
    """Удаляет клиента из инбаундов-заглушек."""
    _, client_uuid = database.get_user_sub_id(tg_id)
    if not client_uuid:
        return
    for stub_id in config.EXPIRED_INBOUND_IDS:
        xui.delete_client(stub_id, client_uuid)