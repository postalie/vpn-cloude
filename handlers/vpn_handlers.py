from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database import get_user, decrease_balance, add_subscription, get_subscription_info, get_discount, use_discount
from config import VPN_PRICE
from keyboards import get_buy_vpn_kb
from states import BuyStates
from datetime import datetime


router = Router()

import uuid
from config import BASE_URL, GITHUB_PAGE_URL
import urllib.parse
import base64
import requests

from utils import shorten_url, encrypt_subscription_happ, get_happ_github_link

from keyboards import get_clients_kb, get_subscription_menu_kb, get_device_action_kb, get_buy_vpn_kb

@router.callback_query(F.data == "connection")
async def show_connection_menu(callback: types.CallbackQuery, state: FSMContext):
    sub_data = await get_subscription_info(callback.from_user.id)
    
    has_active_sub = False
    if sub_data and sub_data[0] and sub_data[1]:
        expires_at, is_active = sub_data[1], sub_data[2]
        expiry_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        if expiry_dt > datetime.now() and is_active:
            has_active_sub = True
            sub_uuid = sub_data[0]

    if has_active_sub:
        try:
            loading_msg = await callback.message.edit_text(
                "<b>🔃 Загружаем настройки подключения...</b>",
                parse_mode="HTML"
            )
        except:
            loading_msg = await callback.message.answer(
                "<b>🔃 Загружаем настройки подключения...</b>",
                parse_mode="HTML"
            )
        
        domain_clean = BASE_URL.replace("https://", "").replace("http://", "")

        # Генерируем github ссылку (она правильно зашифрована)
        github_link = get_happ_github_link(callback.from_user.id, sub_uuid, domain_clean)
        # Сокращаем
        short_link = shorten_url(github_link)

        # QR и кнопка используют одну и ту же ссылку — НЕТ второго запроса к crypto.happ.su
        encoded_qr_data = urllib.parse.quote(short_link)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_qr_data}"
        
        await loading_msg.delete()
        
        data = await state.get_data()
        old_msgs = data.get("last_sub_messages", [])
        for mid in old_msgs:
            try:
                await callback.bot.delete_message(callback.from_user.id, mid)
            except:
                pass

        msg_photo = await callback.message.answer_photo(
            photo=qr_url,
            caption=(
                f"✅ <b>Подписка активна!</b>\n"
                f"\n"
                f"📅 Статус: <code>Безлимитный доступ</code>\n\n"
                f"📸 <b>Способ 1 (сканирование):</b>\n"
                f"Отсканируйте код выше для мгновенного импорта\n\n"
                f"❗ <b>Важно:</b> Для правильной работы перед подключением убедитесь, что все другие VPN отключены."
            ),
            parse_mode="HTML"
        )

        msg_text = await callback.message.answer(
            f"🔗 <b>Способ 2 (быстрый переход):</b>\n"
            f"1️⃣ Нажмите на кнопку <b>«🔗 Ссылка на подписку»</b>\n"
            f"2️⃣ Откроется страница с настройками\n"
            f"3️⃣ Скопируйте ссылку или нажмите «Открыть в Happ»\n\n"
            f"<i>💡 Для стабильной работы сайта требуется отключить VPN сервисы!</i>\n",
            parse_mode="HTML",
            reply_markup=get_device_action_kb(short_link)
        )
        
        await state.update_data(last_sub_messages=[msg_photo.message_id, msg_text.message_id])
        await callback.answer()

    else:
        user = await get_user(callback.from_user.id)
        balance = user[3]
        text = (
            f"💎 <b>Оформление подписки</b>\n"
            f"\n"
            f"У вас пока нет активной подписки.\n\n"
            f"<b>Что вы получите:</b>\n"
            f"✅ Доступ к 15+ локациям\n"
            f"✅ Безлимитный трафик\n"
            f"✅ Работает в РФ на любом операторе\n"
            f"✅ До 5 устройств одновременно\n\n"
            f"💰 Цена: <b>{VPN_PRICE} руб.</b>\n"
            f"💳 Ваш баланс: <b>{balance} руб.</b>\n"
            f"\n"
        )
        
        kb = get_buy_vpn_kb(VPN_PRICE)
        kb.inline_keyboard.append([types.InlineKeyboardButton(text="🗺 Список локаций", callback_data="view_locations")])
        kb.inline_keyboard.append([types.InlineKeyboardButton(text="« Назад в меню", callback_data="back_to_main")])
        
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "show_clients")
async def show_clients_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("📱 <b>Выберите вашу платформу:</b>", reply_markup=get_clients_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "help_connection")
async def show_help_connection(callback: types.CallbackQuery):
    text = (
    "🆘 <b>Помощь и поддержка</b>\n\n"
    "📖 <b>Как подключиться:</b>\n"
    "1️⃣ Установите VPN-клиент\n"
    "   └ <code>Подключить / Купить VPN → Клиенты → </code>\n\n"
    "2️⃣ Получите ссылку подписки\n"
    "   └ <code>Подключить / Купить VPN → Подключить VPN</code>\n\n"
    "3️⃣ Добавьте подписку в приложение\n"
    "   └ Нажмите кнопку «Подключить» или QR-код\n\n"
    "\n"
    "❓ <b>Нужна помощь?</b>\n"
    "Возникли проблемы?\n"
    "Напишите нашему администратору:\n\n"
    "👤 @avestb\n\n"
)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="connection")]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "reset_link")
async def reset_link_handler(callback: types.CallbackQuery, state: FSMContext):
    from database import reset_subscription_uuid
    sub_data = await get_subscription_info(callback.from_user.id)
    if not sub_data or not sub_data[2]: 
         await callback.answer("У вас нет активной подписки для сброса.", show_alert=True)
         return

    # 1. Сначала уведомляем пользователя
    await callback.answer("🔄 Сбрасываем ссылку...", show_alert=True)

    # 2. Сбрасываем в базе
    await reset_subscription_uuid(callback.from_user.id)
    
    # 3. Удаляем текущие сообщения (фото и текст)
    data = await state.get_data()
    old_msgs = data.get("last_sub_messages", [])
    
    # Добавляем ID текущего сообщения, если его там нет
    curr_id = callback.message.message_id
    if curr_id not in old_msgs:
        old_msgs.append(curr_id)

    for mid in old_msgs:
        try:
            await callback.bot.delete_message(callback.from_user.id, mid)
        except:
            pass
            
    # Очищаем список старых сообщений в памяти
    await state.update_data(last_sub_messages=[])
    
    # 4. Отправляем НОВОЕ меню (оно создаст новые сообщения)
    # Вызываем с небольшим флагом или просто полагаемся на то что edit_text упадет и сработает answer
    await show_connection_menu(callback, state)


@router.callback_query(F.data == "view_locations")
async def view_locations(callback: types.CallbackQuery, state: FSMContext):
    import urllib.parse
    from database import get_all_server_nodes
    nodes = await get_all_server_nodes()
    if not nodes:
        await callback.answer("Серверов пока нет", show_alert=True)
        return
    
    # 1. Чистим старые сообщения (фото + текст), если они есть
    data = await state.get_data()
    old_msgs = data.get("last_sub_messages", [])
    for mid in old_msgs:
        try:
            await callback.bot.delete_message(callback.from_user.id, mid)
        except:
            pass
    await state.update_data(last_sub_messages=[])

    # 2. Удаляем само сообщение, с которого перешли
    try:
        await callback.message.delete()
    except:
        pass

    locations = []
    for node_data, name in nodes:
        loc_name = name if name else (node_data.split("#")[-1] if "#" in node_data else "Server")
        
        try:
            loc_name = urllib.parse.unquote(loc_name)
        except:
            pass
        
        locations.append(f"📍 {loc_name}")
    
    text = "🌍 <b>Доступные локации:</b>\n\n" + "\n".join(locations)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="connection")]])
    
    # 3. Отправляем НОВОЕ сообщение
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "enter_discount")
async def ask_discount(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🏷 Введите код купона на скидку:")
    await state.set_state(BuyStates.waiting_for_discount)
    await callback.answer()

@router.message(BuyStates.waiting_for_discount)
async def apply_discount(message: types.Message, state: FSMContext):
    code = message.text.strip()
    discount = await get_discount(code)
    
    if not discount or discount[1] <= 0:
        await message.answer("❌ Купон не найден или закончился.")
        # Возвращаем меню с обычной ценой
        await message.answer(f"Цена: {VPN_PRICE} руб.", reply_markup=get_buy_vpn_kb(VPN_PRICE))
        await state.clear()
        return
    
    percent = discount[0]
    new_price = int(VPN_PRICE * (1 - percent / 100))
    if new_price < 0: new_price = 0
    
    await state.update_data(current_price=new_price, used_discount=code)
    
    await message.answer(
        f"✅ Купон применен! Скидка {percent}%.\n"
        f"Новая цена: {new_price} руб.",
        reply_markup=get_buy_vpn_kb(new_price)
    )
    await state.set_state(None)

@router.callback_query(F.data == "buy_confirm")
async def process_purchase(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    price = data.get("current_price", VPN_PRICE)
    discount_code = data.get("used_discount")
    
    user_id = callback.from_user.id
    
    # Списываем деньги
    success = await decrease_balance(user_id, price)
    if not success:
        await callback.answer("❌ Недостаточно средств на балансе!", show_alert=True)
        return
    
    # Если был купон, списываем активацию
    if discount_code:
        await use_discount(discount_code)
    
    # Продлеваем или создаем подписку
    from database import extend_subscription
    existing = await get_subscription_info(user_id)
    
    if existing:
        await extend_subscription(user_id, days=3650) # Продлеваем на 10 лет
    else:
        sub_uuid = str(uuid.uuid4())
        await add_subscription(user_id, sub_uuid, days=3650) # Создаем на 10 лет
    
    # Всегда берем свежие данные из базы после записи/обновления
    fresh_info = await get_subscription_info(user_id)
    sub_uuid = fresh_info[0]
    
    # Формируем ссылку подписки нового формата: domain/user_id/uuid
    sub_link = f"{BASE_URL}/{user_id}/{sub_uuid}"
    
    # Дата "навсегда"
    expiry_date = "01.01.2099"

    # Формируем deep link для Happ (через редирект)
    # Формируем зашифрованную и сокращенную ссылку через GitHub Pages
    domain_clean = BASE_URL.replace("https://", "").replace("http://", "")
    gh_link = get_happ_github_link(user_id, sub_uuid, domain_clean)
    short_gh_link = shorten_url(gh_link)

    # Используем клавиатуру с короткой ссылкой
    kb = get_device_action_kb(short_gh_link)

    await callback.message.edit_text(
        f"💎 <b>Подписка оформлена!</b>\n\n"
        f"Поздравляем! Теперь вам доступен интернет без ограничений\n\n"
        f"📅 Срок действия: <b>до {expiry_date}</b>\n\n"
        f"Нажмите на кнопку ниже, чтобы получить настройки подключения и QR-код 👇",
        parse_mode="HTML",
        reply_markup=kb
    )
    await state.clear()


@router.callback_query(F.data == "back_to_sub")
async def back_to_subscription(callback: types.CallbackQuery, state: FSMContext):
    # Просто вызываем хендлер показа подписки
    await show_connection_menu(callback, state)