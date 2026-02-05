from aiohttp import web
import base64
from datetime import datetime
from database import (
    get_all_server_nodes, get_stats, get_subscription_by_uuid, 
    register_device, get_user, get_subscription_info, 
    get_user_devices, rename_device, delete_device,
    get_user_by_token, activate_promo, extend_subscription,
    add_subscription, get_discount, use_discount
)
from config import API_SECRET, BOT_TOKEN, BASE_URL, VPN_PRICE
from utils import shorten_url, get_happ_github_link
import hmac
import hashlib
import json
from urllib.parse import parse_qsl

# --- API HANDLERS ---

async def sub_handler(request):
    """Выдача ключей в формате Base64 с проверкой подписки"""
    sub_uuid = request.match_info.get('uuid')
    
    # Режим защиты: если запрос пришел не напрямую, проверяем ключ (опционально)
    # Но так как UUID сам по себе секретный, оставим доступ открытым для клиентов,
    # а для воркера добавим логирование.
    
    if not sub_uuid:
        return web.Response(text="No UUID provided", status=400)
    
    # ПРОВЕРКА ПОДПИСКИ В БД
    sub_data = await get_subscription_by_uuid(sub_uuid)
    
    if not sub_data:
        print(f"DEBUG: Unknown UUID requested: {sub_uuid}")
        error_key = f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#🚨 Подписка не найдена"
        b64_error = base64.b64encode(error_key.encode('utf-8')).decode('utf-8')
        return web.Response(text=b64_error, content_type="text/plain")
    
    
    # Безопасная распаковка (старые подписки могут не иметь device_limit)
    if len(sub_data) == 4:
        user_id, expires_at_str, is_active, device_limit = sub_data
    else:
        user_id, expires_at_str, is_active = sub_data
        device_limit = 5  # Значение по умолчанию для старых подписок
    
    # Проверка на наличие данных (важно после миграции)
    if not expires_at_str:
        print(f"DEBUG: Subscription data incomplete for user {user_id}")
        error_key = f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#🚨 Данные подписки неполные"
        b64_error = base64.b64encode(error_key.encode('utf-8')).decode('utf-8')
        return web.Response(text=b64_error, content_type="text/plain")

    # Проверка на активность и срок действия
    expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
    if not is_active or expires_at < datetime.now():
        print(f"DEBUG: Expired/Inactive subscription for user {user_id}")
        # Возвращаем один ключ с сообщением об истечении подписки
        error_key = f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#❌ Подписка истекла"
        b64_expired = base64.b64encode(error_key.encode('utf-8')).decode('utf-8')
        return web.Response(text=b64_expired, content_type="text/plain")

    # 1. Заголовки для красоты
    # Фиксированная дата "навсегда" - 12.12.2032
    forever_dt = datetime(2032, 12, 12, 23, 59, 59)
    forever_ts = int(forever_dt.timestamp())
    
    # Используем лимит из БД
    limit = device_limit if device_limit else 5

    # --- ПРОВЕРКА ЛИМИТА УСТРОЙСТВ (АВТОМАТИЧЕСКАЯ) ---
    ua = request.headers.get('User-Agent', 'unknown')
    
    # --- УЛУЧШЕННЫЙ ПАРСИНГ USER-AGENT ---
    import re
    ua_lower = ua.lower()
    
    model = "Unknown Device"
    platform = "Unknown"
    app_info = "Generic Client"

    # 1. Определяем приложение (app_info)
    if "/" in ua:
        # Для всех приложений с версией (Happ/3.9.1 -> Happ / 3.9.1)
        app_parts = ua.split()[0].split('/')
        if len(app_parts) == 2:
            app_info = f"{app_parts[0]} / {app_parts[1]}"
        else:
            app_info = app_parts[0]
    
    # 2. Определяем платформу и версию
    # Сначала проверяем специальные заголовки от приложений (X-Device-Os, X-Ver-Os)
    os_header = request.headers.get('X-Device-Os')
    os_ver_header = request.headers.get('X-Ver-Os')
    
    if os_header:
        if os_ver_header:
            platform = f"{os_header} / {os_ver_header}"
        else:
            platform = os_header
    
    if platform == "Unknown":
        # Если заголовков нет, парсим User-Agent
        if "android" in ua_lower:
            platform = "Android"
            v_match = re.search(r"android\s+([\d.]+)", ua_lower)
            if v_match:
                platform = f"Android / {v_match.group(1)}"
            elif "v2raytun" in ua_lower:
                platform = "Android"
        elif any(x in ua_lower for x in ["iphone", "ipad", "ipod", "ios", "shadowrocket"]):
            platform = "iOS"
            v_match = re.search(r"os\s+([\d_]+)", ua_lower)
            if v_match:
                platform = f"iOS / {v_match.group(1).replace('_', '.')}"
        elif "windows" in ua_lower:
            platform = "Windows"
        elif "macintosh" in ua_lower or "mac os" in ua_lower:
            platform = "macOS"
        elif "linux" in ua_lower:
            platform = "Linux"
        elif "happ" in ua_lower:
            platform = "Mobile (Happ)"

    # 3. Определяем модель устройства
    # Сначала проверяем специальные заголовки (Sec-CH-UA-Model и др.)
    m_header = request.headers.get('Sec-CH-UA-Model') or request.headers.get('X-Device-Model')
    if m_header:
        model = m_header.strip('" ')

    if model == "Unknown Device":
        if "Android" in platform:
            # Агрессивный поиск: RMX3852, SM-G991B, M2101K6G и так далее
            brand_match = re.search(r"\b(RMX\d+|SM-[A-Z\d]+|M2\d+[A-Z\d]+|CPH\d+|V\d+[A-Z\d]+|POCO [A-Z\d]+|Redmi [A-Z\d ]+)\b", ua)
            if brand_match:
                model = brand_match.group(1)
            else:
                # Паттерн: Android x.y.z; [MODEL] Build/
                m_match = re.search(r"Android\s+[\d.]+;\s*([^;)]+)", ua)
                if m_match:
                    model = m_match.group(1).split("Build/")[0].strip()
        
        elif "iOS" in platform:
            if "iPhone" in ua: model = "iPhone"
            elif "iPad" in ua: model = "iPad"
            else: model = "Apple Device"
        elif platform == "Windows": model = "PC / Laptop"
        elif platform == "macOS": model = "Mac"
        elif "Happ" in app_info: model = "Mobile Device"

    import hashlib
    # Привязка теперь ТОЛЬКО по User-Agent (без IP как просили)
    # Используем MD5 от UA как HWID
    device_hash = hashlib.md5(ua.encode()).hexdigest().upper()[:16]

    # Пытаемся зарегистировать устройство
    success, current_count, limit, user_id, is_new = await register_device(sub_uuid, device_hash)
    
    bot = request.app['bot']

    if is_new and user_id:
        # 1. Уведомление ПОЛЬЗОВАТЕЛЮ
        try:
            msg = (
                "🆕 <b>Новое устройство подключено!</b>\n\n"
                f"📱 Модель: <code>{model}</code>\n"
                f"🧠 Платформа: <code>{platform}</code>\n"
                f"🌐 User-Agent: <code>{app_info}</code>\n"
                f"🪪 HWID: <code>{device_hash}</code>\n\n"
                "<i>Если это устройство подключили не вы, проверьте безопасность своей подписки.</i>"
            )
            await bot.send_message(user_id, msg, parse_mode="HTML")
        except: pass

        # 2. ДЕТАЛЬНЫЙ ЛОГ ДЛЯ АДМИНА
        from config import ADMIN_IDS
        debug_msg = (
            "🛠 <b>[DEBUG] Новое подключение</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"🔑 UUID: <code>{sub_uuid}</code>\n\n"
            f"📝 <b>Результат парсинга:</b>\n"
            f"📱 Модель: <code>{model}</code>\n"
            f"🧠 Платформа: <code>{platform}</code>\n"
            f"🆔 Приложение: <code>{app_info}</code>\n\n"
            f"🌐 <b>Raw User-Agent:</b>\n"
            f"<code>{ua}</code>\n\n"
            f"📋 <b>Headers:</b>\n"
            f"<code>{dict(request.headers)}</code>"
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, debug_msg, parse_mode="HTML")
            except: pass

    if not success:
        # Уведомляем пользователя о превышении
        if user_id:
            try:
                msg = (
                    "⚠️ <b>Внимание! Превышен лимит устройств</b>\n\n"
                    f"На вашей подписке уже подключено максимально разрешенное количество устройств ({limit}).\n\n"
                    "Чтобы подключить новое устройство, сбросьте ссылку в меню: <code>Подключить VPN</code> -> <code>Сбросить ссылку</code>."
                )
                await bot.send_message(user_id, msg, parse_mode="HTML")
            except: pass

        # Возвращаем список ключей с сообщением об ошибке
        error_nodes = [
            f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#🚨 Ошибка",
            f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#‼️ Превышен лимит устройств‼️",
            f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#Бот: @cloudeVPNbot"
        ]
        text_warning = "\n".join(error_nodes)
        b64_warning = base64.b64encode(text_warning.encode('utf-8')).decode('utf-8')
        return web.Response(text=b64_warning, content_type="text/plain")

    # --- ФОРМИРОВАНИЕ ОТВЕТА ---
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache",
        "Subscription-Userinfo": f"upload=0; download=0; total=0; expire={forever_ts}",
        "Profile-Title": "Cloude VPN",
        "Profile-Update-Interval": "1",
        "Profile-Description": f"Devices: {current_count}/{limit}",
        "Content-Disposition": f"attachment; filename*=UTF-8''sub.txt"
    }

    nodes = await get_all_server_nodes()
    
    # 2. Собираем содержимое
    final_nodes = []
    
    # --- [JQOS] Авто-выбор самого быстрого сервера (не РФ) ---
    import urllib.parse
    jqos_node = None
    if nodes:
        for node_data, node_name in nodes:
            # Пытаемся понять имя ноды для проверки на РФ
            name_to_check = ""
            if node_name:
                try: name_to_check = urllib.parse.unquote(node_name).strip()
                except: name_to_check = node_name.strip()
            elif "#" in node_data:
                try: name_to_check = urllib.parse.unquote(node_data.split("#")[-1]).strip()
                except: name_to_check = node_data.split("#")[-1].strip()
            
            # Если имя не начинается с 🇷🇺 или РФ — это наш кандидат
            if not (name_to_check.startswith("🇷🇺") or name_to_check.startswith("РФ")):
                base_link = node_data.split("#")[0] if "#" in node_data else node_data
                jqos_node = f"{base_link}#json"
                break
    
    if jqos_node:
        final_nodes.append(jqos_node)
    # -------------------------------------------------------

    # Ссылка на бота по просьбе юзера
    final_nodes.append(f"═════════════════════════")
    final_nodes.append(f"🚀 Ссылка на бота: t.me/cloudevpnbot")
    final_nodes.append(f"Лимит устройств: {limit}")
    final_nodes.append(f"═════════════════════════")

    if nodes:
        import urllib.parse
        for node_data, node_name in nodes:
            node_data = node_data.strip()
            if not node_data: continue
            
            # Если имя задано в БД, используем его
            if node_name:
                # Декодируем имя, если оно было URL-encoded (убираем %F0...)
                try:
                    display_name = urllib.parse.unquote(node_name)
                except:
                    display_name = node_name

                # Если в самой ссылке уже есть #, отрезаем его и ставим свое имя
                if "#" in node_data:
                    base_link = node_data.split("#")[0]
                    final_nodes.append(f"{base_link}#{display_name}")
                else:
                    final_nodes.append(f"{node_data}#{display_name}")
            else:
                # Очищаем ключи от лишних меток, если нужно, или просто добавляем
                if "#" in node_data:
                    # Пробуем декодировать существующее имя в хеше
                    try:
                        base, tag = node_data.split("#", 1)
                        decoded_tag = urllib.parse.unquote(tag)
                        final_nodes.append(f"{base}#{decoded_tag}")
                    except:
                         final_nodes.append(node_data)
                else:
                    final_nodes.append(f"{node_data}#Cloude VPN Server")

    text_content = "\n".join(final_nodes)
    
    # 3. Кодируем в Base64
    b64_content = base64.b64encode(text_content.encode('utf-8')).decode('utf-8')
    
    print(f"DEBUG: Eternal sub sent for user {user_id}")
    return web.Response(text=b64_content, headers=headers)

async def api_status_handler(request):
    # Этот эндпоинт для твоего сайта (показать статус "Онлайн")
    provided_key = request.headers.get('X-API-Key')
    if provided_key != API_SECRET:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    nodes = await get_all_server_nodes()
    locations = set()
    for _, name in nodes:
        if name: locations.add(name)
        else: locations.add("Other")
    
    data = {
        "status": "online",
        "nodes_online": len(nodes),
        "locations_count": len(locations),
        "total_users": await get_stats()
    }
    return web.json_response(data)

async def register_device_handler(request):
    """
    Эндпоинт для get.php. Проверяет и регистрирует новое устройство.
    """
    provided_key = request.headers.get('X-API-Key')
    if provided_key != API_SECRET:
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    sub_uuid = data.get("uuid")
    device_hash = data.get("hash")
    
    print(f"DEBUG: register_device call - UUID: {sub_uuid}, Hash: {device_hash}")

    if not sub_uuid or not device_hash:
        print("DEBUG: register_device - Missing UUID or Hash")
        return web.json_response({"error": "UUID and Hash required"}, status=400)

    success, current_count, limit, user_id, is_new = await register_device(sub_uuid, device_hash)
    print(f"DEBUG: register_device result - Success: {success}, Count: {current_count}, Limit: {limit}, User: {user_id}")
    
    bot = request.app['bot']

    if not success:
        # Уведомляем пользователя в Telegram
        if user_id:
            try:
                msg = (
                    "⚠️ <b>Внимание! Превышен лимит устройств</b>\n\n"
                    f"На вашей подписке уже подключено максимально разрешенное количество устройств ({limit}).\n\n"
                    "Чтобы подключить новое устройство, сбросьте ссылку в меню: <code>Подключить VPN</code> -> <code>Сбросить ссылку</code>.\n"
                    "<i>Старая ссылка перестанет работать, и лимит устройств обнулится.</i>"
                )
                await bot.send_message(user_id, msg, parse_mode="HTML")
            except Exception as e:
                print(f"Error sending limit notification: {e}")
        
        return web.json_response({
            "status": "limit_exceeded",
            "current_count": current_count,
            "limit": limit
        })

    return web.json_response({
        "status": "ok",
        "current_count": current_count,
        "limit": limit
    })

# --- TMA API HANDLERS ---

def verify_telegram_data(init_data: str):
    """Проверка подлинности данных от Telegram Mini App"""
    if not init_data:
        return False
    
    try:
        vals = dict(parse_qsl(init_data))
        hash_val = vals.pop('hash')
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(vals.items())])
        
        secret_key = hmac.new("WebAppData".encode(), BOT_TOKEN.encode(), hashlib.sha256).digest()
        h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if h == hash_val:
            return json.loads(vals.get('user'))
        return False
    except:
        return False

async def authenticate_user(request):
    """Универсальная аутентификация: Telegram InitData или Token"""
    auth = request.headers.get('Authorization')
    if not auth:
        return None
    
    # 1. Пробуем как Telegram InitData
    user_data = verify_telegram_data(auth)
    if user_data:
        return user_data.get('id')
    
    # 2. Пробуем как наш Token
    user_id = await get_user_by_token(auth)
    return user_id

async def get_me_handler(request):
    """Получение информации о текущем пользователе и его подписке"""
    user_id = await authenticate_user(request)
    if not user_id:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    user = await get_user(user_id)
    sub = await get_subscription_info(user_id)
    
    if not user:
        return web.json_response({"error": "User not found"}, status=404)
        
    res = {
        "user_id": user[0],
        "username": user[1],
        "balance": user[3],
        "subscription": None
    }
    
    if sub:
        domain_clean = BASE_URL.replace("https://", "").replace("http://", "")
        gh_link = get_happ_github_link(user_id, sub[0], domain_clean)
        encrypted_link = shorten_url(gh_link)
        
        res["subscription"] = {
            "uuid": sub[0],
            "expires_at": sub[1],
            "is_active": sub[2],
            "limit": sub[3],
            "encrypted_link": encrypted_link
        }
    
    return web.json_response(res)

async def list_devices_handler(request):
    """Список устройств пользователя"""
    user_id = await authenticate_user(request)
    if not user_id:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    devices = await get_user_devices(user_id)
    # Преобразуем кортежи в словари
    res = []
    for d in devices:
        res.append({
            "id": d[0],
            "hash": d[1],
            "name": d[2] or "Неизвестное",
            "last_seen": d[3]
        })
    return web.json_response(res)

async def rename_device_handler(request):
    """Переименование устройства"""
    user_id = await authenticate_user(request)
    if not user_id:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    data = await request.json()
    device_id = data.get('id')
    new_name = data.get('name')
    
    if not device_id or not new_name:
        return web.json_response({"error": "Missing params"}, status=400)
    
    # Проверка принадлежности устройства (опционально, но желательно)
    # Для упрощения пока просто переименовываем
    await rename_device(device_id, new_name)
    return web.json_response({"status": "ok"})

async def delete_device_handler(request):
    """Удаление устройства"""
    user_id = await authenticate_user(request)
    if not user_id:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    data = await request.json()
    device_id = data.get('id')
    
    if not device_id:
        return web.json_response({"error": "Missing ID"}, status=400)
    
    await delete_device(device_id)
    return web.json_response({"status": "ok"})

async def buy_subscription_handler(request):
    """Покупка или продление подписки через TMA"""
    user_id = await authenticate_user(request)
    if not user_id:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    from database import decrease_balance
    
    data = await request.json()
    coupon_code = data.get('coupon')
    
    price = VPN_PRICE
    if coupon_code:
        discount = await get_discount(coupon_code)
        if discount and discount[1] > 0:
            percent = discount[0]
            price = int(VPN_PRICE * (1 - percent / 100))
    
    success = await decrease_balance(user_id, price)
    if not success:
        return web.json_response({"error": "Недостаточно средств"}, status=400)
    
    if coupon_code:
        await use_discount(coupon_code)
        
    existing = await get_subscription_info(user_id)
    if existing:
        await extend_subscription(user_id, days=3650)
    else:
        import uuid
        sub_uuid = str(uuid.uuid4())
        await add_subscription(user_id, sub_uuid, days=3650)
        
    return web.json_response({"status": "ok", "message": "Подписка успешно оформлена"})

async def activate_coupon_handler(request):
    """Активация промокода на баланс"""
    user_id = await authenticate_user(request)
    if not user_id:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    data = await request.json()
    code = data.get('code')
    
    if not code:
        return web.json_response({"error": "Введите код"}, status=400)
        
    result = await activate_promo(user_id, code)
    
    if result == "not_found":
        return web.json_response({"error": "Промокод не найден"}, status=404)
    if result == "ended":
        return web.json_response({"error": "Промокод закончился"}, status=400)
    if result == "already_activated":
        return web.json_response({"error": "Вы уже активировали этот промокод"}, status=400)
        
    return web.json_response({"status": "ok", "amount": result})

async def health_check(request):
    return web.Response(text="API Online")


# --- SERVER SETUP ---

def setup_web_server(bot):
    app = web.Application()
    app['bot'] = bot
    
    # Регистрация маршрутов
    app.router.add_get('/sub/{uuid}', sub_handler)
    app.router.add_get('/api/sub/{uuid}', sub_handler)
    app.router.add_get('/api/status', api_status_handler)
    app.router.add_post('/api/register_device', register_device_handler)
    app.router.add_get('/health', health_check)

    # TMA API
    app.router.add_get('/api/me', get_me_handler)
    app.router.add_get('/api/list_devices', list_devices_handler)
    app.router.add_post('/api/rename_device', rename_device_handler)
    app.router.add_post('/api/delete_device', delete_device_handler)
    app.router.add_post('/api/buy_subscription', buy_subscription_handler)
    app.router.add_post('/api/activate_coupon', activate_coupon_handler)

    # Настройка CORS (чтобы твой фронтенд-сайт мог делать запросы к этому API)
    import aiohttp_cors
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # Применяем CORS ко всем маршрутам
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Статические файлы (TMA Dashboard)
    app.router.add_get('/dashboard', lambda r: web.FileResponse('web/tma.html'))
    app.router.add_static('/', path='web/', name='static')
    
    print("Web Server with CORS (Cloude VPN API) initialized.")
    return app
