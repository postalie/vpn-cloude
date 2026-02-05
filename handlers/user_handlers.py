from aiogram import Router, F, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from database import add_user, get_user, verify_user, add_referral_activation, get_referral_link, add_balance, get_device_count
from keyboards import get_main_menu, get_captcha_kb
from config import ADMIN_IDS
from aiogram.types import ReplyKeyboardRemove

router = Router()

# Обработка старых текстовых кнопок (для очистки интерфейса)
@router.message(F.text.in_({
    "⚡ Купить VPN", "👤 Профиль", "🎁 Промокоды", "ℹ️ Помощь",
    "⚡ Продлить VPN", "🔌 Подключение", "Купить VPN", "Промокоды", "Профиль", "Помощь"
}))
async def handle_old_keyboard(message: types.Message):
    welcome_text = (
        f"👋 <b>Меню обновлено!</b>\n\n"
        "Мы перешли на более удобные кнопки. Пожалуйста, используйте меню ниже 👇"
    )
    msg = await message.answer("🛠", reply_markup=ReplyKeyboardRemove())
    await msg.delete()
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_menu(message.from_user.id))

@router.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    user = await get_user(message.from_user.id)
    referral_code = command.args if command.args else None
    
    is_new_user = False
    if not user:
        is_new_user = True
        await add_user(message.from_user.id, message.from_user.full_name)
    
    # Обработка реферальной ссылки для НОВЫХ пользователей
    bonus_text = ""
    if is_new_user and referral_code:
        # Пробуем активировать рефку
        if await add_referral_activation(message.from_user.id, referral_code):
            ref_info = await get_referral_link(referral_code)
            if ref_info:
                bonus_amount = ref_info[0]
                if bonus_amount > 0:
                    await add_balance(message.from_user.id, bonus_amount)
                    bonus_text = f"\n\n🎁 <b>Вам начислено {bonus_amount} руб. по приглашению!</b>"

    # Теперь логика показа приветствия
    user = await get_user(message.from_user.id) # Перечитываем юзера
    
    if not user[2]: # Не верифицирован
        import uuid
        rand_code = uuid.uuid4().hex[:8]
        await message.answer(
            "☁️ <b>Cloude VPN — Твой личный безопасный интернет</b>\n\n"
            "Добро пожаловать! Мы создали сервис, который открывает любые сайты и приложения на максимальной скорости.\n\n"
            "⚡ <b>Без ограничений</b>\n"
            "🛡️ <b>Полная анонимность</b>\n"
            "🌍 <b>Лучшие локации</b>"
            f"{bonus_text}\n\n"
            "Чтобы продолжить, подтвердите, что вы человек 👇",
            parse_mode="HTML",
            reply_markup=get_captcha_kb(rand_code)
        )
        msg = await message.answer("🛠", reply_markup=ReplyKeyboardRemove())
        await msg.delete()
    else:
        msg = await message.answer("🛠", reply_markup=ReplyKeyboardRemove())
        await msg.delete()
        welcome_text = (
            f"👋 <b>Рады видеть тебя, {message.from_user.full_name}!</b>\n\n"
            "Чтобы подключить VPN или пополнить баланс, используй меню ниже 👇"
        )
        await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_menu(message.from_user.id))

@router.callback_query(F.data.startswith("captcha_"))
async def captcha_solved(callback: types.CallbackQuery, state: FSMContext):
    await verify_user(callback.from_user.id)
    await callback.message.delete()
    # Убираем клавиатуру (ReplyKeyboardRemove)
    msg = await callback.message.answer("✅ Подключено", reply_markup=ReplyKeyboardRemove())
    await msg.delete()
    # И сразу следом главное меню
    await callback.message.answer("Загружаем меню...", reply_markup=await get_main_menu(callback.from_user.id))

@router.callback_query(F.data == "profile")
async def show_profile_callback(callback: types.CallbackQuery):
    user = await get_user(callback.from_user.id)
    if user:
        # user structure: id, username, verified, balance
        from database import get_subscription_info
        sub_info = await get_subscription_info(callback.from_user.id)
        
        status = "❌ Не активна"
        if sub_info and sub_info[2]:
            status = "✅ Активна (Безлимит)"
            
        limit = sub_info[3] if sub_info else 5
        current_devices = await get_device_count(callback.from_user.id)
        
        text = (
            f"👤 <b>Личный кабинет</b>\n"
            f"\n"
            f"🆔 Ваш ID: <code>{user[0]}</code>\n"
            f"💰 Баланс: <b>{user[3]} руб.</b>\n\n"
            f"💎 Подписка: <b>{status}</b>\n"
            f"📱 Устройств: <b>{current_devices} из {limit}</b>\n"
            f"\n\n"
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="top_up_balance")],
            [InlineKeyboardButton(text="« Назад в меню", callback_data="back_to_main")]
        ])

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "help")
async def show_help_callback(callback: types.CallbackQuery):
    text = (
        "🚀 <b>Cloude VPN</b> — ваш надежный проводник в свободный интернет.\n\n"
        "🔹 <b>Протокол:</b> VLESS + Reality\n"
        "🔹 <b>Скорость:</b> До 1 Гбит/с без ограничений.\n"
        "🔹 <b>Устройства:</b> До 5 устройств на одну подписку.\n"
        "🔹 <b>Приватность:</b> Мы не храним логи ваших посещений.\n\n"
        "📖 <b>Как пользоваться:</b>\n"
        "1. Пополните баланс в Профиле -> Пополнить баланс.\n"
        "2. Нажмите «⚡️ Купить VPN».\n"
        "3. Следуйте инструкциям по подключению.\n\n"
        "🆘 <b>Поддержка:</b> Если возникли вопросы, обращайтесь к @soldenchain."
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    # При возврате в главное меню чистим всё за собой
    data = await state.get_data()
    old_msgs = data.get("last_sub_messages", [])
    for mid in old_msgs:
        try:
            await callback.bot.delete_message(callback.from_user.id, mid)
        except:
            pass
    await state.update_data(last_sub_messages=[])
    
    # Удаляем само сообщение с кнопкой "Назад"
    try:
        await callback.message.delete()
    except:
        pass

    text = (
        f"👋 <b>Рады видеть тебя, {callback.from_user.full_name}!</b>\n\n"
        "Чтобы подключить VPN или пополнить баланс, используй меню ниже 👇"
    )
    # Отправляем НОВОЕ сообщение вместо редактирования
    await callback.message.answer(text, parse_mode="HTML", reply_markup=await get_main_menu(callback.from_user.id))
    await callback.answer()

