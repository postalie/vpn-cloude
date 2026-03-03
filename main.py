import os
import sys
import asyncio
import logging
import ssl

sys.dont_write_bytecode = True

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import create_tables
from handlers import user_handlers, promo_handlers, admin_handlers, vpn_handlers, pay_handlers

# Логирование
logging.basicConfig(level=logging.INFO)

from aiohttp import web
from web_server import setup_web_server

async def main():
    # Создаем таблицы
    await create_tables()

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем роутеры
    dp.include_router(user_handlers.router)
    dp.include_router(promo_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(vpn_handlers.router)
    dp.include_router(pay_handlers.router)

    # Запуск веб-сервера для подписок
    port = int(os.environ.get("PORT", 8080))
    app = setup_web_server(bot)
    runner = web.AppRunner(app)
    await runner.setup()

    # SSL контекст (если сертификаты существуют)
    ssl_context = None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ssl_cert = os.path.join(script_dir, "ssl", "server.crt")
    ssl_key = os.path.join(script_dir, "ssl", "server.key")

    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(ssl_cert, ssl_key)
        print(f"🔐 HTTPS включен")

    site = web.TCPSite(runner, '0.0.0.0', port, ssl_context=ssl_context)
    await site.start()

    protocol = "https" if ssl_context else "http"
    print(f"Бот запущен. Сервер подписок работает на порту {port} ({protocol})...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
