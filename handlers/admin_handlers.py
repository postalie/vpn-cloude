import os
import io
import uuid
import sqlite3
import shutil
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import ADMIN_IDS, DB_NAME
from keyboards import (
    admin_main_kb, admin_promo_kb, admin_subs_kb, admin_servers_kb, 
    admin_db_kb, get_nodes_management_kb, get_users_list_kb, get_user_manage_kb,
    admin_referral_main_kb, get_referrals_list_kb
)
from states import AdminStates
from database import (
    get_stats, create_promo, create_discount, add_key_to_stock, 
    add_server_node, clear_server_nodes, get_all_server_nodes, 
    get_keys_count, get_all_users, delete_subscription, add_subscription,
    get_all_server_nodes_admin, toggle_node_status, delete_node_by_id, edit_node_name, edit_node_data,
    get_subscription_info, set_device_limit, set_balance, get_user, activate_subscription,
    create_referral_link, get_all_referral_links, delete_referral_link, reset_subscription_uuid, get_device_count
)

router = Router()

# Фильтр на админа
def is_admin(user_id: int):
    return user_id in ADMIN_IDS

# --- НАВИГАЦИЯ ---

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("🔧 <b>Админ-панель Cloude VPN</b>\n\nВыберите нужный раздел для управления сервисом:", 
                         reply_markup=admin_main_kb, parse_mode="HTML")

@router.callback_query(F.data == "admin_back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("🔧 <b>Админ-панель Cloude VPN</b>\n\nВыберите нужный раздел для управления сервисом:", 
                                     reply_markup=admin_main_kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "adm_promo_cat")
async def promo_cat(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("🎁 <b>Управление промокодами и скидками</b>", reply_markup=admin_promo_kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "adm_subs_cat")
async def subs_cat(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("💎 <b>Управление подписками пользователей</b>", reply_markup=admin_subs_kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "adm_nodes_cat")
async def nodes_cat(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("🔑 <b>Управление общими ключами (Пул)</b>", reply_markup=admin_servers_kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "adm_db_cat")
async def db_cat(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("💾 <b>База данных и экспорт</b>", reply_markup=admin_db_kb, parse_mode="HTML")
    await callback.answer()

# --- СТАТИСТИКА ---

@router.callback_query(F.data == "admin_stats")
@router.callback_query(F.data == "adm_stats_nodes")
async def show_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    count = await get_stats()
    nodes = await get_all_server_nodes()
    stock_keys = await get_keys_count()
    
    text = (
        f"📊 <b>Общая статистика сервиса:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Всего пользователей: <b>{count}</b>\n"
        f"🔑 Ключей в пуле (Sub): <b>{len(nodes)}</b>\n"
        f"📦 Ключей на складе: <b>{stock_keys}</b>\n"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# --- ПРОМОКОДЫ ---

@router.callback_query(F.data == "admin_create_promo")
async def ask_promo_details(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("✍️ Введите <code>код сумма количество</code>\nПример: <code>GIFT500 500 10</code>", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_promo_data)
    await callback.answer()

@router.message(AdminStates.waiting_for_promo_data)
async def process_create_promo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        data = message.text.split()
        code, amount, activations = data[0], int(data[1]), int(data[2])
        await create_promo(code, amount, activations)
        await message.answer(f"✅ Промокод <code>{code}</code> на {amount} руб. создан!", parse_mode="HTML")
        await state.clear()
    except:
        await message.answer("❌ Ошибка формата.")

@router.callback_query(F.data == "admin_create_discount")
async def ask_discount_details(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("✍️ Введите <code>код процент количество</code>\nПример: <code>SALE30 30 100</code>", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_discount_data)
    await callback.answer()

@router.message(AdminStates.waiting_for_discount_data)
async def process_create_discount(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        data = message.text.split()
        code, percent, activations = data[0], int(data[1]), int(data[2])
        await create_discount(code, percent, activations)
        await message.answer(f"✅ Скидка <code>{code}</code> на {percent}% создана!", parse_mode="HTML")
        await state.clear()
    except:
        await message.answer("❌ Ошибка формата.")

# --- ПОДПИСКИ ---

@router.callback_query(F.data == "admin_gift_vpn")
async def gift_vpn_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("🎁 Введите Telegram ID пользователя:")
    await state.set_state(AdminStates.waiting_for_user_id_gift)
    await callback.answer()

@router.message(AdminStates.waiting_for_user_id_gift)
async def process_gift_vpn(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        target_id = int(message.text.strip())
        sub_uuid = str(uuid.uuid4())
        await add_subscription(target_id, sub_uuid)
        await message.answer(f"✅ Подписка выдана <code>{target_id}</code>", parse_mode="HTML")
        await state.clear()
    except:
        await message.answer("❌ Ошибка.")

@router.callback_query(F.data == "admin_clear_vpn")
async def clear_vpn_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("🗑 Введите ID для ДЕАКТИВАЦИИ подписки:")
    await state.set_state(AdminStates.waiting_for_user_id_clear)
    await callback.answer()

@router.message(AdminStates.waiting_for_user_id_clear)
async def process_clear_vpn(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        target_id = int(message.text.strip())
        await delete_subscription(target_id)
        await message.answer(f"✅ Подписка <code>{target_id}</code> деактивирована. При следующем обновлении пользователь увидит сообщение об истечении.", parse_mode="HTML")
        await state.clear()
    except:
        await message.answer("❌ Ошибка.")

# --- РЕФЕРАЛЬНЫЕ ССЫЛКИ ---

@router.callback_query(F.data == "admin_referrals_cat")
async def referral_cat(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("🔗 <b>Управление реферальными ссылками</b>\n\nЗдесь вы можете создавать ссылки, по которым новые пользователи будут получать бонус при первом входе.", reply_markup=admin_referral_main_kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_create_ref")
async def ask_ref_details(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("✍️ Введите <code>код бонус коммент</code>\nПример: <code>VLOGER 100 Ссылка для блогера</code>", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_ref_data)
    await callback.answer()

@router.message(AdminStates.waiting_for_ref_data)
async def process_create_ref(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split(maxsplit=2)
        code = parts[0]
        bonus = int(parts[1])
        comment = parts[2] if len(parts) > 2 else "Нет комментария"
        
        await create_referral_link(code, bonus, comment)
        await message.answer(f"✅ Реф. ссылка <code>{code}</code> создана!\nБонус: {bonus} руб.\nСсылка: <code>https://t.me/{(await message.bot.get_me()).username}?start={code}</code>", parse_mode="HTML")
        await state.clear()
    except Exception as e:
        await message.answer("❌ Ошибка формата. Введите: <code>код бонус коммент</code>")

@router.callback_query(F.data == "admin_list_refs")
async def admin_list_refs(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    refs = await get_all_referral_links()
    if not refs:
        await callback.answer("У вас пока нет реферальных ссылок", show_alert=True)
        return
    
    await callback.message.edit_text("📋 <b>Список всех реферальных ссылок:</b>", reply_markup=get_referrals_list_kb(refs), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_del_ref_"))
async def adm_del_ref(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    code = callback.data.replace("adm_del_ref_", "")
    await delete_referral_link(code)
    await callback.answer(f"✅ Рефка {code} удалена!", show_alert=True)
    
    refs = await get_all_referral_links()
    if not refs:
        await callback.message.edit_text("🔗 <b>Реферальные ссылки</b>", reply_markup=admin_referral_main_kb)
    else:
        await callback.message.edit_reply_markup(reply_markup=get_referrals_list_kb(refs))

# --- КЛЮЧИ (POOL) ---

@router.callback_query(F.data == "admin_add_nodes_btn")
async def admin_add_nodes_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("📥 Пришлите список ключей (vless/vmess) одним сообщением или загрузите <b>.txt</b> файл:", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_server_nodes)
    await callback.answer()

@router.message(AdminStates.waiting_for_server_nodes)
async def process_server_nodes(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    
    nodes_to_add = []
    
    # Обработка документа (.txt)
    if message.document:
        if not message.document.file_name.endswith('.txt'):
            await message.answer("❌ Пожалуйста, присылайте только <b>.txt</b> файлы.", parse_mode="HTML")
            return
        
        file = await message.bot.get_file(message.document.file_id)
        downloaded = await message.bot.download_file(file.file_path)
        content = downloaded.read().decode('utf-8')
        nodes_to_add = [line.strip() for line in content.splitlines() if line.strip()]
        
    # Обработка текста
    elif message.text:
        nodes_to_add = [line.strip() for line in message.text.splitlines() if line.strip()]
    
    if not nodes_to_add:
        await message.answer("❌ Список ключей пуст.")
        return

    count = 0
    for node in nodes_to_add:
        await add_server_node(node)
        count += 1
        
    await message.answer(f"✅ Добавлено <b>{count}</b> ключей в пул.", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "admin_clear_nodes_btn")
async def admin_clear_nodes_confirm(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await clear_server_nodes()
    await callback.message.answer("🗑 Пул ключей полностью очищен.")
    await callback.answer()

@router.callback_query(F.data == "admin_list_nodes")
@router.callback_query(F.data.startswith("nodes_page_"))
async def admin_list_nodes_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    page = 0
    if callback.data.startswith("nodes_page_"):
        page = int(callback.data.split("_")[-1])
        
    nodes = await get_all_server_nodes_admin()
    if not nodes:
        await callback.message.edit_text("❌ В пуле пока нет серверов.", reply_markup=admin_servers_kb)
        return
    
    # Расчет общего кол-ва страниц
    total_pages = (len(nodes) + 9) // 10
    
    text = (
        f"🖥 <b>Управление серверами</b> (Стр. {page+1}/{total_pages})\n\n"
        "Нажмите на кнопку с названием, чтобы включить/выключить сервер. Выключенные серверы не попадают в подписку."
    )
    
    await callback.message.edit_text(text, 
                                     reply_markup=get_nodes_management_kb(nodes, page=page), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("node_toggle_"))
async def admin_toggle_node(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    parts = callback.data.split("_")
    node_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 0
    
    await toggle_node_status(node_id)
    
    nodes = await get_all_server_nodes_admin()
    await callback.message.edit_reply_markup(reply_markup=get_nodes_management_kb(nodes, page=page))
    await callback.answer("Статус изменен")

@router.callback_query(F.data.startswith("node_delete_"))
async def admin_delete_node(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    parts = callback.data.split("_")
    node_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 0
    
    await delete_node_by_id(node_id)
    
    nodes = await get_all_server_nodes_admin()
    if not nodes:
        await callback.message.edit_text("❌ В пуле пока нет серверов.", reply_markup=admin_servers_kb)
    else:
        # Проверка если страница стала пустой после удаления
        if page > 0 and page * 10 >= len(nodes):
            page -= 1
        await callback.message.edit_reply_markup(reply_markup=get_nodes_management_kb(nodes, page=page))
    await callback.answer("Сервер удален")

@router.callback_query(F.data.startswith("node_rename_"))
async def admin_rename_node_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    node_id = int(callback.data.split("_")[-1])
    await state.update_data(rename_node_id=node_id)
    await callback.message.answer("✍️ Введите новое название (локацию) для этого сервера:\nНапример: <code>Германия 🇩🇪</code>", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_node_name)
    await callback.answer()

@router.message(AdminStates.waiting_for_node_name)
async def process_node_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    node_id = data.get("rename_node_id")
    new_name = message.text.strip()
    
    await edit_node_name(node_id, new_name)
    await message.answer(f"✅ Название сервера изменено на: <b>{new_name}</b>", parse_mode="HTML")
    await state.clear()
    
    # Показываем список снова
    nodes = await get_all_server_nodes_admin()
    await message.answer("🖥 Управление серверами:", reply_markup=get_nodes_management_kb(nodes))

@router.callback_query(F.data.startswith("node_editkey_"))
async def admin_edit_key_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    node_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_node_id=node_id)
    await callback.message.answer("🔑 Пришлите новый ключ (vless/vmess) для этого сервера:")
    await state.set_state(AdminStates.waiting_for_node_data)
    await callback.answer()

@router.message(AdminStates.waiting_for_node_data)
async def process_node_data(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    node_id = data.get("edit_node_id")
    new_data = message.text.strip()
    
    if not new_data.startswith(("vless://", "vmess://", "trojan://", "ss://")):
        await message.answer("❌ Ошибка. Ключ должен начинаться с vless://, vmess:// и т.д.")
        return

    await edit_node_data(node_id, new_data)
    await message.answer(f"✅ Данные ключа успешно обновлены!", parse_mode="HTML")
    await state.clear()
    
    # Показываем список снова
    nodes = await get_all_server_nodes_admin()
    await message.answer("🖥 Управление серверами:", reply_markup=get_nodes_management_kb(nodes))

# --- УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (НОВОЕ) ---

@router.callback_query(F.data == "admin_users_list")
async def admin_users_list_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    users = await get_all_users()
    if not users:
        await callback.answer("Пользователей еще нет", show_alert=True)
        return
    await callback.message.edit_text("👤 <b>Список пользователей:</b>", reply_markup=get_users_list_kb(users), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_manage_user_"))
async def admin_manage_user_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[-1])
    
    sub_info = await get_subscription_info(user_id)
    user_data = await get_user(user_id)
    
    status = "✅ Активна" if sub_info and sub_info[2] else "❌ Нет подписки (или отключена)"
    limit = sub_info[3] if sub_info else "Не задан"
    is_active = bool(sub_info and sub_info[2])
    current_devices = await get_device_count(user_id)
    
    text = (
        f"👤 <b>Управление пользователем</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Имя: {user_data[1]}\n"
        f"💰 Баланс: {user_data[3]} руб.\n"
        f"💎 Подписка: {status}\n"
        f"📱 Устройств: <b>{current_devices} из {limit}</b>"
    )
    
    await callback.message.edit_text(text, reply_markup=get_user_manage_kb(user_id, has_sub=bool(sub_info), is_active=is_active), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_gift_sub_"))
async def admin_gift_sub_fast(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[-1])
    sub_uuid = str(uuid.uuid4())
    await add_subscription(user_id, sub_uuid, days=3650)
    await callback.answer("✅ Подписка выдана на 10 лет", show_alert=True)
    # Возвращаемся в меню юзера
    await admin_manage_user_handler(callback)

@router.callback_query(F.data.startswith("adm_del_sub_"))
async def admin_del_sub_fast(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[-1])
    await delete_subscription(user_id)
    await callback.answer("🗑 Подписка деактивирована", show_alert=True)
    # Возвращаемся в меню юзера
    await admin_manage_user_handler(callback)

@router.callback_query(F.data.startswith("adm_restore_sub_"))
async def admin_restore_sub_fast(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[-1])
    await activate_subscription(user_id)
    await callback.answer("✅ Подписка включена обратно", show_alert=True)
    # Возвращаемся в меню юзера
    await admin_manage_user_handler(callback)

@router.callback_query(F.data.startswith("adm_limit_user_"))
async def admin_limit_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(manage_user_id=user_id)
    await callback.message.answer(f"📱 Введите новый лимит устройств для <code>{user_id}</code>:", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_user_limit)
    await callback.answer()

@router.callback_query(F.data.startswith("adm_reset_uuid_"))
async def admin_reset_uuid_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[-1])
    
    # Сбрасываем UUID
    await reset_subscription_uuid(user_id)
    
    # Уведомляем админа
    await callback.answer("✅ UUID сброшен и устройства очищены", show_alert=True)
    
    # Уведомляем пользователя
    try:
        msg = (
            "🔄 <b>Администратор обновил вашу ссылку подписки</b>\n\n"
            "Ваша старая ссылка и все подключенные устройства больше не действительны.\n\n"
            "Пожалуйста, получите новую ссылку в меню:\n"
            "<code>🚀 Подключить / Купить VPN</code> -> <code>Настройка подключения</code>"
        )
        await callback.bot.send_message(user_id, msg, parse_mode="HTML")
    except Exception as e:
        print(f"Error notifying user about UUID reset: {e}")
    
    # Возвращаемся в меню юзера
    await admin_manage_user_handler(callback)

@router.message(AdminStates.waiting_for_user_limit)
async def process_user_limit(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        limit = int(message.text.strip())
        data = await state.get_data()
        user_id = data.get("manage_user_id")
        await set_device_limit(user_id, limit)
        await message.answer(f"✅ Лимит устройств для <code>{user_id}</code> изменен на {limit}", parse_mode="HTML")
        await state.clear()
    except:
        await message.answer("❌ Ошибка. Введите число.")

@router.callback_query(F.data.startswith("adm_balance_user_"))
async def admin_balance_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(manage_user_id=user_id)
    await callback.message.answer(f"💰 Введите новый баланс для <code>{user_id}</code>:", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_user_balance)
    await callback.answer()

@router.message(AdminStates.waiting_for_user_balance)
async def process_user_balance(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        amount = int(message.text.strip())
        data = await state.get_data()
        user_id = data.get("manage_user_id")
        await set_balance(user_id, amount)
        await message.answer(f"✅ Баланс <code>{user_id}</code> изменен на {amount} руб.", parse_mode="HTML")
        await state.clear()
    except:
        await message.answer("❌ Ошибка. Введите число.")

# --- РАССЫЛКА ---

@router.callback_query(F.data == "admin_broadcast_start")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("📢 <b>Рассылка сообщений</b>\n\nВведите текст сообщения, которое получат все пользователи бота. Поддерживается HTML разметка.", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast_text)
async def process_broadcast_text_preview(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    text = message.text
    
    # Сохраняем текст в состояние
    await state.update_data(broadcast_text=text)
    
    # Клавиатура подтверждения
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_broadcast"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")
        ]
    ])
    
    await message.answer(
        f"📢 <b>Предпросмотр рассылки:</b>\n\n"
        f"{text}\n\n"
        f"<i>Вы уверены, что хотите отправить это сообщение всем пользователям?</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_broadcast_confirm)

@router.callback_query(AdminStates.waiting_for_broadcast_confirm, F.data.in_({"confirm_broadcast", "cancel_broadcast"}))
async def process_broadcast_decision(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    
    if callback.data == "cancel_broadcast":
        await callback.message.edit_text("❌ Рассылка отменена.")
        await state.clear()
        return

    # Если подтвердили
    data = await state.get_data()
    text = data.get("broadcast_text")
    
    if not text:
        await callback.message.edit_text("❌ Ошибка: Текст рассылки потерян.")
        await state.clear()
        return

    from database import get_all_users_ids
    users_ids = await get_all_users_ids()
    
    sent_count = 0
    await callback.message.edit_text(f"⏳ Начинаю рассылку на {len(users_ids)} пользователей...")
    
    for uid in users_ids:
        try:
            await callback.message.bot.send_message(uid, text, parse_mode="HTML")
            sent_count += 1
        except Exception:
            pass # Бот заблокирован и т.д.
            
    await callback.message.answer(f"✅ Рассылка завершена. Доставлено: {sent_count} из {len(users_ids)}")
    await state.clear()

# --- ЭКСПОРТ И БАЗА ---

@router.callback_query(F.data == "admin_export_users_sql")
async def export_users_sql(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    # Генерируем SQL Dump (только таблицы пользователей)
    conn = sqlite3.connect(DB_NAME)
    sql_dump = ""
    for line in conn.iterdump():
        sql_dump += f"{line}\n"
    conn.close()
    
    output = io.BytesIO(sql_dump.encode('utf-8'))
    file = types.BufferedInputFile(output.read(), filename="database_dump.sql")
    await callback.message.answer_document(file, caption="💾 Полный дамп базы данных (.sql)")
    await callback.answer()

@router.callback_query(F.data == "admin_export_nodes_txt")
async def export_nodes_txt(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    nodes = await get_all_server_nodes(only_active=False)
    if not nodes:
        await callback.answer("Пул пуст", show_alert=True)
        return
    
    # Формируем список ключей с названиями из панели управления
    keys_list = []
    for node_data, node_name in nodes:
        node_data = node_data.strip()
        if not node_data:
            continue
        
        # Если название задано в панели управления, используем его
        if node_name:
            # Убираем старое название из ключа (если есть) и добавляем новое
            if "#" in node_data:
                base_key = node_data.split("#")[0]
                keys_list.append(f"{base_key}#{node_name}")
            else:
                keys_list.append(f"{node_data}#{node_name}")
        else:
            # Если названия нет, оставляем ключ как есть
            keys_list.append(node_data)
    
    text = "\n".join(keys_list)
    output = io.BytesIO(text.encode('utf-8'))
    file = types.BufferedInputFile(output.read(), filename="keys_pool.txt")
    await callback.message.answer_document(file, caption=f"🔑 Пул ключей ({len(nodes)} шт.)")
    await callback.answer()

@router.callback_query(F.data == "admin_export_devices_json")
async def export_devices_data(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    # 1. Пытаемся взять devices.json
    json_path = os.path.join(os.getcwd(), 'web', 'devices.json')
    if os.path.exists(json_path):
        from aiogram.types import FSInputFile
        file = FSInputFile(json_path)
        await callback.message.answer_document(file, caption="📱 Файл привязок устройств (PHP JSON)")
    
    # 2. Экспортируем таблицу devices из БД в TXT для удобства
    import aiosqlite
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT sub_uuid, device_hash FROM devices') as cursor:
            rows = await cursor.fetchall()
    
    if rows:
        text_data = "UUID | Device Hash\n" + "-"*30 + "\n"
        for row in rows:
            text_data += f"{row[0]} | {row[1]}\n"
        
        output = io.BytesIO(text_data.encode('utf-8'))
        file_db = types.BufferedInputFile(output.read(), filename="devices_db_export.txt")
        await callback.message.answer_document(file_db, caption=f"📊 Выгрузка устройств из БД ({len(rows)} записей)")
    elif not os.path.exists(json_path):
        await callback.answer("Данных об устройствах пока нет", show_alert=True)
        return

    await callback.answer()

@router.callback_query(F.data == "admin_download_db")
async def download_db_file(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    from aiogram.types import FSInputFile
    if os.path.exists(DB_NAME):
        file = FSInputFile(DB_NAME)
        await callback.message.answer_document(file, caption="💾 Оригинальный файл базы данных SQLite")
    else:
        await callback.answer("Файл БД еще не создан", show_alert=True)
    await callback.answer()

@router.callback_query(F.data == "admin_export_data_zip")
async def export_data_zip(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    import shutil
    db_dir = os.path.dirname(DB_NAME)
    
    if not os.path.exists(db_dir) or not os.listdir(db_dir):
        await callback.answer("Папка с данными пуста или не создана", show_alert=True)
        return

    # Создаем архив
    archive_name = "database_backup"
    shutil.make_archive(archive_name, 'zip', db_dir)
    
    from aiogram.types import FSInputFile
    file = FSInputFile(f"{archive_name}.zip")
    await callback.message.answer_document(file, caption="📦 Полный бэкап папки с данными (ZIP)")
    
    # Удаляем временный архив после отправки
    os.remove(f"{archive_name}.zip")
    await callback.answer()
