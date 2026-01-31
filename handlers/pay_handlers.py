from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database import get_user, update_balance
from keyboards import get_payment_methods_kb, get_crypto_currencies_kb, get_payment_check_kb
from states import PayStates
from utils.crypto_bot import crypto_bot

router = Router()

@router.callback_query(F.data == "adm_balance_user_self") # Если вдруг понадобится
@router.callback_query(F.data == "top_up_balance")
async def start_top_up(callback: types.CallbackQuery, state: FSMContext):
    # Спрашиваем сумму
    await callback.message.answer("💰 Введите сумму пополнения в рублях (минимум 50):")
    await state.set_state(PayStates.waiting_for_amount)
    await callback.answer()

@router.message(PayStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 50:
            await message.answer("❌ Минимальная сумма пополнения — 50 руб.\nВведите сумму еще раз:")
            return
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return

    await state.update_data(pay_amount=amount)
    # Предлагаем методы
    await message.answer(f"💳 Сумма к оплате: {amount} руб.\nВыберите способ оплаты:", reply_markup=get_payment_methods_kb())
    # Сбрасываем стейт, так как дальше выбор кнопками
    await state.set_state(None)

@router.callback_query(F.data == "pay_crypto")
async def select_crypto_method(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data.get("pay_amount")
    if not amount:
        await callback.message.edit_text("❌ Ошибка: сессия истекла. Начните заново.")
        return

    await callback.message.edit_text(
        f"💎 Выберите криптовалюту для оплаты {amount} руб.:",
        reply_markup=get_crypto_currencies_kb(amount)
    )

@router.callback_query(F.data.startswith("pay_asset_"))
async def create_invoice_handler(callback: types.CallbackQuery, state: FSMContext):
    asset = callback.data.split("_")[-1] # TON, USDT, ...
    data = await state.get_data()
    amount_rub = data.get("pay_amount")
    
    if not amount_rub:
        await callback.message.edit_text("❌ Ошибка: сессия истекла.")
        return

    # CryptoBot принимает сумму в крипте, либо в фиате но создает инвойс.
    # Метод createInvoice принимает amount как string.
    # Если мы хотим выставить счет в рублях, но получить крипту, CryptoBot позволяет указывать fiat amount?
    # В документации CryptoBot createInvoice:
    # amount: String. Amount of the invoice in floating point number.
    # asset: String. Currency code. Supported assets: TON, BTC, ETH, USDT, USDC, BUSD.
    # 
    # ОДНАКО, createInvoice не конвертирует автоматически из RUB в TON в самом методе (напрямую).
    # Но есть метод getExchangeRates. Мы пока сделаем просто: курсы примерные или используем CryptoPay API currency feature.
    # Стоп, CryptoBot API позволяет указывать `currency_type="fiat"` и `fiat="RUB"`? 
    # Нет, в простом методе createInvoice мы указываем ASSET (крипту) и AMOUNT (в крипте).
    # 
    # НО! Есть createInvoice за фиат? Обычно боты делают конвертацию сами.
    # Для простоты, пока будем считать, что нам нужно сконвертировать RUB -> ASSET.
    # Получим курс.
    
    rates = await crypto_bot._request("GET", "getExchangeRates")
    # rates format: [{'is_valid': True, 'source': 'USDT', 'target': 'RUB', 'rate': '95.50'}, ...]
    
    rate = None
    if rates and rates.get('ok'):
        for r in rates['result']:
            if r['source'] == asset and r['target'] == 'RUB':
                rate = float(r['rate'])
                break
    
    if not rate:
        # Fallback rates (заглушка)
        fallback_rates = {"USDT": 100, "TON": 250, "BTC": 6000000, "TRX": 15}
        rate = fallback_rates.get(asset, 100)
    
    # Считаем сумму в крипте
    amount_crypto = amount_rub / rate
    # Округляем до 6 знаков
    amount_crypto = f"{amount_crypto:.6f}"

    description = f"Пополнение баланса на {amount_rub} RUB ({amount_crypto} {asset})"
    
    # Payload: user_id:amount_rub
    payload = f"{callback.from_user.id}:{amount_rub}"

    invoice = await crypto_bot.create_invoice(amount_crypto, asset, description, payload)
    
    if not invoice:
        await callback.answer("❌ Ошибка создания счета CryptoBot", show_alert=True)
        return

    invoice_id = invoice['invoice_id']
    pay_url = invoice['pay_url'] # или bot_invoice_url (обычно pay_url ведет на веб-форму или бота)
    # Используем mini_app_invoice_url или bot_invoice_url если есть
    url = invoice.get('mini_app_invoice_url') or invoice.get('bot_invoice_url') or invoice.get('pay_url')
    
    await callback.message.edit_text(
        f"💳 <b>Счет на оплату создан!</b>\n\n"
        f"Сумма: <b>{amount_crypto} {asset}</b>\n"
        f"({amount_rub} RUB)\n\n"
        f"🔗 Нажмите кнопку ниже для оплаты, затем нажмите «Проверить оплату».",
        reply_markup=get_payment_check_kb(url, invoice_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("check_pay_"))
async def check_payment_handler(callback: types.CallbackQuery):
    invoice_id = callback.data.split("_")[-1]
    
    invoice = await crypto_bot.get_invoice(invoice_id)
    if not invoice:
        await callback.answer("❌ Счет не найден.", show_alert=True)
        return
    
    status = invoice['status'] # active, paid, expired
    
    if status == 'paid':
        # Проверяем, не начислен ли уже?
        # В payload у нас user_id:amount
        payload = invoice.get('payload')
        if not payload:
             await callback.answer("❌ Ошибка payload", show_alert=True)
             return
             
        user_id_str, amount_str = payload.split(":")
        user_id = int(user_id_str)
        amount = int(amount_str)
        
        # Тут по-хорошему нужно сохранять ID инвойса в БД чтобы не начислить дважды.
        # Но так как у нас нет таблицы платежей, проверим просто:
        # CryptoBot удаляет paid инвойсы? Нет.
        # Мы можем использовать hidden_message_id или просто положиться на честность (плохо)
        # ЛУЧШЕ: просто начислить и скажем пользователю "Успешно".
        # Но если он нажмет еще раз?
        # Для защиты: CryptoBot инвойс имеет 'paid_at'. Если он старый - игнорим? Нет.
        # Правильно: завести таблицу payments (id, user_id, amount, status, invoice_id).
        # Но пользователь просил "отдельный файл", не меняя слишком структуру.
        # Ок, сделаем проверку "на лету" - если статус paid, мы начисляем и...
        # Как пометить что мы УЖЕ начислили?
        # Мы не сохраняем invoice_id в БД. Это проблема.
        # Решение: Добавить таблицу payments в create_tables в database.py?
        # Или, просто для MVP сейчас:
        # При создании инвойса мы ничего не пишем.
        # При проверке: если paid, мы начисляем.
        # Чтобы не начислить дважды, нам НУЖНО хранить обработанные инвойсы.
        # Давай добавим простую таблицу payments_history в database.py.
        pass
        # Пока просто заглушка с начислением (риск дабл спенда если юзер будет тыкать)
        # Но invoice меняет статус? Нет, он остается paid.
        # Придется добавить таблицу.
        
        from database import is_invoice_processed, add_invoice_processed
        if await is_invoice_processed(invoice_id):
             await callback.message.edit_text("✅ Этот счет уже оплачен и зачислен.")
             return

        await add_invoice_processed(invoice_id, user_id, amount)
        await update_balance(user_id, amount)
        
        await callback.message.edit_text(f"✅ <b>Оплата прошла успешно!</b>\nБаланс пополнен на {amount} руб.", parse_mode="HTML")
        
    elif status == 'active':
        await callback.answer("⏳ Оплата еще не поступила. Попробуйте через минуту.", show_alert=True)
    else:
        await callback.message.edit_text(f"❌ Статус счета: {status}")
