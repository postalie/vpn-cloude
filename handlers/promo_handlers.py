from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from keyboards import promo_menu
from states import PromoStates
from database import activate_promo

router = Router()

@router.callback_query(F.data == "promo")
async def show_promo_menu(callback: types.CallbackQuery):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    # Копируем клавиатуру или изменяем существующую (добавляем назад)
    # promo_menu импортирован, но он Reply или Inline? Inline (см keyboards.py).
    # Но нам нужно добавить кнопку Назад.
    # Проще пересоздать или изменить объект. InlineKeyboardMarkup имеет inline_keyboard (list of list).
    
    new_kb = InlineKeyboardMarkup(inline_keyboard=[
        *promo_menu.inline_keyboard,
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text("👇 Выберите действие:", reply_markup=new_kb)

@router.callback_query(F.data == "activate_promo")
async def ask_promo_code(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введите промокод:")
    await state.set_state(PromoStates.waiting_for_code)
    await callback.answer()

@router.message(PromoStates.waiting_for_code)
async def process_promo_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    result = await activate_promo(message.from_user.id, code)
    
    if result == "not_found":
        await message.answer("❌ Промокод не найден.")
    elif result == "ended":
        await message.answer("❌ Промокод закончился.")
    elif result == "already_activated":
        await message.answer("❌ Вы уже активировали этот промокод.")
    else:
        await message.answer(f"✅ Промокод активирован! Начислено: <b>{result} руб.</b>", parse_mode="HTML")
    
    await state.clear()
