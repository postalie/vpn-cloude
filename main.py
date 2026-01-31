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
    site = web.TCPSite(runner, '0.0.0.0', port) 
    await site.start()
    
    print(f"Бот запущен. Сервер подписок работает на порту {port}...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
