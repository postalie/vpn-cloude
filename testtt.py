import requests
import json
import uuid
import urllib3
import urllib.parse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVERS = [
    # {
    #     "ip": "158.160.201.209",
    #     "proto": "https",
    #     "port": 30151,
    #     "path": "nLs6KJj8WIArkUGIf5",
    #     "inbound_id": 9,
    #     "remark": "🇩🇪 Германия"
    # },
    {
        "ip": "158.160.201.209",
        "proto": "https",
        "port": 30151,
        "path": "nLs6KJj8WIArkUGIf5",
        "inbound_id": 5,
        "remark": "🇳🇱 Нидерланды"
    },
    {
        "ip": "144.31.169.61",
        "proto": "https",
        "port": 14409,
        "path": "wWcO4udR5JORXdpxSc",
        "inbound_id": 2,
        "remark": "🇫🇮 Финляндия"
    },
    {
        "ip": "158.160.201.209",
        "proto": "https",
        "port": 30151,
        "path": "nLs6KJj8WIArkUGIf5",
        "inbound_id": 6,
        "remark": "🇸🇪 Швеция"
    },
    {
        "ip": "158.160.201.209",
        "proto": "https",
        "port": 30151,
        "path": "nLs6KJj8WIArkUGIf5",
        "inbound_id": 7,
        "remark": "🇪🇪 Эстония"
    },
    {
        "ip": "51.250.94.95",
        "proto": "http",
        "port": 2053,
        "path": "4u45MJZmftYPzDsP2v",
        "inbound_id": 1,
        "remark": "🇷🇺 Обход №1"
    },
    {
        "ip": "178.154.195.229",
        "proto": "https",
        "port": 18604,
        "path": "6FXDkpWZKYBLsLBtBU",
        "inbound_id": 3,
        "remark": "🇷🇺 Обход №2"
    },
    {
        "ip": "84.201.128.119",
        "proto": "https",
        "port": 50944,
        "path": "dFBsj7GWtHBpVozpZ8",
        "inbound_id": 2,
        "remark": "🇷🇺 Обход №3"
    }
]

USER_LOGIN = "14"
PASS_LOGIN = "88"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/x-www-form-urlencoded",
}


def get_session(base_url):
    """Создаёт сессию и логинится"""
    s = requests.Session()
    s.headers.update(headers)

    resp = s.post(
        f"{base_url}/login",
        data={"username": USER_LOGIN, "password": PASS_LOGIN},
        timeout=12,
        verify=False
    )

    if resp.status_code != 200 or "success" not in resp.text.lower():
        print(f"   ✗ Не удалось авторизоваться на {base_url}")
        return None

    return s


def get_inbound_info(session, base_url, inbound_id):
    """Получает информацию об inbound"""
    r = session.get(
        f"{base_url}/panel/api/inbounds/get/{inbound_id}",
        timeout=12,
        verify=False
    )

    if r.status_code != 200:
        print(f"   ✗ Не удалось получить inbound (HTTP {r.status_code})")
        return None

    obj = r.json().get("obj")
    if not obj:
        print("   ✗ Нет obj в ответе")
        return None

    return obj


def generate_vless_link(user_uuid, srv, obj):
    """Генерирует vless-ссылку"""
    port = obj.get("port", "443")
    stream_str = obj.get("streamSettings", "{}")
    stream = json.loads(stream_str)

    network = stream.get("network", "tcp")
    security = stream.get("security", "none")

    # Принудительно tcp, если что-то другое
    if network != "tcp":
        print(f"   ⚠ Transport был {network} → принудительно tcp")
        network = "tcp"

    pbk = sni = sid = spx = fp = ""
    if security == "reality":
        reality = stream.get("realitySettings", {})
        settings = reality.get("settings", {})
        pbk = settings.get("publicKey", "")
        fp = settings.get("fingerprint", "chrome")
        spx = settings.get("spiderX", "/")
        sni = reality.get("serverNames", [""])[0]
        sid = reality.get("shortIds", [""])[0]

    link = (
        f"vless://{user_uuid}@{srv['ip']}:{port}"
        f"?type=tcp&security={security}&pbk={pbk}&fp={fp}"
        f"&sni={sni}&sid={sid}&spx={urllib.parse.quote(spx)}"
        f"&flow=xtls-rprx-vision#{srv['remark']}"
    )

    return link


def add_user(user_uuid=None, email_prefix="user"):
    """
    Добавляет пользователя (клиента) по UUID на все сервера
    Если user_uuid не передан — генерирует новый
    Возвращает список ссылок
    """
    if user_uuid is None:
        user_uuid = str(uuid.uuid4())
        print(f"Новый UUID создан: {user_uuid}")
    else:
        print(f"Используется существующий UUID: {user_uuid}")

    ready_links = []

    for srv in SERVERS:
        base_url = f"{srv['proto']}://{srv['ip']}:{srv['port']}/{srv['path'].rstrip('/')}".rstrip('/')
        print(f"\n→ {srv['remark']} ({srv['ip']})")

        session = get_session(base_url)
        if not session:
            continue

        obj = get_inbound_info(session, base_url, srv["inbound_id"])
        if not obj:
            continue

        # Генерируем ссылку
        link = generate_vless_link(user_uuid, srv, obj)
        ready_links.append(link)
        print(f"   Ссылка: {link}")

        # Добавляем клиента
        add_url = f"{base_url}/panel/api/inbounds/addClient"
        clients = [{
            "id": user_uuid,
            "flow": "xtls-rprx-vision",
            "email": f"{email_prefix}-{user_uuid[:8]}",
            "enable": True,
            "expiryTime": 0,
            "totalGB": 0,
            "limitIp": 0
        }]

        resp = session.post(add_url, data={
            "id": srv["inbound_id"],
            "settings": json.dumps({"clients": clients})
        }, timeout=12, verify=False)

        if resp.status_code == 200:
            print("   ✓ Клиент добавлен")
        else:
            print(f"   ⚠ Добавление не удалось (HTTP {resp.status_code})")

    print("\n" + "═" * 90)
    print("СОЗДАННЫЕ ССЫЛКИ:")
    print("═" * 90)
    for i, lnk in enumerate(ready_links, 1):
        print(f"{lnk}\n")
    print("═" * 90)

    return ready_links, user_uuid


def delete_user(user_uuid):
    """
    Удаляет клиента по UUID со всех серверов
    """
    print(f"\nУдаление пользователя {user_uuid} со всех серверов...\n")

    for srv in SERVERS:
        base_url = f"{srv['proto']}://{srv['ip']}:{srv['port']}/{srv['path'].rstrip('/')}".rstrip('/')
        print(f"→ {srv['remark']} ({srv['ip']})")

        session = get_session(base_url)
        if not session:
            continue

        # Удаление клиента
        del_url = f"{base_url}/panel/api/inbounds/{srv['inbound_id']}/delClient/{user_uuid}"
        resp = session.post(del_url, timeout=12, verify=False)

        if resp.status_code == 200 and "success" in resp.text.lower():
            print("   ✓ Клиент удалён")
        else:
            print(f"   ⚠ Не удалось удалить (HTTP {resp.status_code}, ответ: {resp.text[:100]})")


# ────────────────────────────────────────────────
# Примеры использования
# ────────────────────────────────────────────────

if __name__ == "__main__":
    print("Выберите действие:")
    print("1 — Создать нового пользователя (добавить ключи)")
    print("2 — Удалить пользователя по UUID")
    choice = input("→ ")

    if choice == "1":
        # Можно передать свой UUID, если нужно
        # add_user("ваш-uuid-здесь")
        add_user()  # новый UUID

    elif choice == "2":
        uuid_to_del = input("Введите UUID для удаления: ").strip()
        if uuid_to_del:
            delete_user(uuid_to_del)
        else:
            print("UUID не введён")
    else:
        print("Неверный выбор")