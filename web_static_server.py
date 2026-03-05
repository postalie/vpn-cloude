#!/usr/bin/env python3
"""
Web Server для TMA Dashboard и статических файлов
Запускается на порту 25666
"""

import os
import sys
import asyncio
import logging
from aiohttp import web
import aiohttp_cors
import base64
import aiosqlite
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# Конфигурация
API_SECRET = "CloudeVpnVOIDAPI_1488"
DB_NAME = "data_base/bot_database.db"

# Импортируем порт из конфига если есть
try:
    from config import WEB_PORT, API_PORT
except ImportError:
    WEB_PORT = 25666
    API_PORT = 8080

API_BASE_URL = f"http://127.0.0.1:{API_PORT}"  # Локальный API сервер

async def get_subscription_by_uuid(sub_uuid):
    """Проверка подписки в БД"""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute(
                'SELECT user_id, expires_at, is_active, device_limit FROM subscriptions WHERE sub_uuid = ?', 
                (sub_uuid,)
            ) as cursor:
                return await cursor.fetchone()
    except Exception as e:
        print(f"DB Error: {e}")
        return None

async def sub_handler(request):
    """Выдача подписки - локальная проверка + прокси на API сервер"""
    sub_uuid = request.match_info.get('uuid')
    
    if not sub_uuid:
        return web.Response(text="No UUID provided", status=400)
    
    # Проверяем подписку локально в БД
    sub_data = await get_subscription_by_uuid(sub_uuid)
    
    if not sub_data:
        print(f"DEBUG: Подписка не найдена: {sub_uuid}")
        error_key = "vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#🚨 Подписка не найдена"
        b64_error = base64.b64encode(error_key.encode('utf-8')).decode('utf-8')
        return web.Response(text=b64_error, content_type="text/plain")
    
    # Безопасная распаковка
    if len(sub_data) == 4:
        user_id, expires_at_str, is_active, device_limit = sub_data
    else:
        user_id, expires_at_str, is_active = sub_data
        device_limit = 5
    
    # Проверка на наличие данных
    if not expires_at_str:
        print(f"DEBUG: Данные подписки неполные: {sub_uuid}")
        error_key = "vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#🚨 Ошибка данных"
        b64_error = base64.b64encode(error_key.encode('utf-8')).decode('utf-8')
        return web.Response(text=b64_error, content_type="text/plain")
    
    # Проверка срока действия
    expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
    if not is_active or expires_at < datetime.now():
        print(f"DEBUG: Подписка истекла: {sub_uuid}")
        error_key = "vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#❌ Подписка истекла"
        b64_error = base64.b64encode(error_key.encode('utf-8')).decode('utf-8')
        return web.Response(text=b64_error, content_type="text/plain")
    
    # Перенаправляем запрос на API сервер (порт 8080) для получения ключей
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/sub/{sub_uuid}") as resp:
                body = await resp.read()
                return web.Response(
                    body=body,
                    status=resp.status,
                    headers=dict(resp.headers)
                )
    except Exception as e:
        print(f"Proxy error: {e}")
        return web.Response(text=f"Error: {str(e)}", status=502)

async def api_proxy_handler(request):
    """Прокси для API запросов"""
    # Получаем путь после /api/
    api_path = request.path.replace('/api/', '', 1)
    target_url = f"{API_BASE_URL}/api/{api_path}{request.rel_url.query_string}"
    
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            # Копируем заголовки
            headers = {k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']}
            
            body = None
            if request.method != 'GET':
                body = await request.read()
            
            async with session.request(
                request.method,
                target_url,
                headers=headers,
                data=body
            ) as resp:
                resp_body = await resp.read()
                return web.Response(
                    body=resp_body,
                    status=resp.status,
                    headers=dict(resp.headers)
                )
    except Exception as e:
        print(f"API Proxy error: {e}")
        return web.json_response({"error": str(e)}, status=502)

async def dashboard_handler(request):
    """Отдача TMA Dashboard"""
    return web.FileResponse('web/tma.html')

async def static_handler(request):
    """Отдача статических файлов"""
    file_path = request.match_info.get('filename', '')
    full_path = os.path.join('web', file_path)
    
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return web.FileResponse(full_path)
    return web.HTTPNotFound()

async def health_handler(request):
    """Health check"""
    return web.json_response({"status": "ok", "port": WEB_PORT})

def setup_web_static():
    app = web.Application()
    
    # CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    
    # Маршруты
    app.router.add_get('/health', health_handler)
    app.router.add_get('/dashboard', dashboard_handler)
    app.router.add_get('/sub/{uuid}', sub_handler)
    app.router.add_route('*', '/api/{path:.*}', api_proxy_handler)
    
    # Статика - конкретные файлы
    app.router.add_get('/web/{filename:.*}', static_handler)
    app.router.add_get('/style.css', lambda r: web.FileResponse('web/style.css'))
    
    # SPA роутинг - все неизвестные запросы отдают tma.html
    async def spa_handler(request):
        return web.FileResponse('web/tma.html')
    
    app.router.add_get('/{path:.*}', spa_handler)

    # Применяем CORS
    for route in list(app.router.routes()):
        cors.add(route)

    print(f"🌐 Web Static Server запущен на порту {WEB_PORT}")
    return app

if __name__ == '__main__':
    from aiohttp import web

    # Проверка что мы в директории проекта
    if not os.path.exists(DB_NAME):
        print(f"❌ База данных не найдена: {DB_NAME}")
        print("   Запускайте из корневой директории проекта")
        sys.exit(1)

    # Проверка что web/tma.html существует
    if not os.path.exists('web/tma.html'):
        print(f"❌ Файл web/tma.html не найден")
        print("   Запускайте из корневой директории проекта")
        sys.exit(1)

    app = setup_web_static()
    web.run_app(app, host='0.0.0.0', port=WEB_PORT)
