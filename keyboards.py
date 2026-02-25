from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import BASE_URL

# Главное меню (Сверхпростое)
def get_main_menu():
 return InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Подключить / Купить VPN", callback_data="connection")],
        [InlineKeyboardButton(text="👤 Мой аккаунт", callback_data="profile"), InlineKeyboardButton(text="🎁 Бонусы", callback_data="promo")]
    ]
)

# Меню выбора метода пополнения
def get_payment_methods_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Crypto Bot", callback_data="pay_crypto")],
            # Можно добавить другие методы, если есть
            [InlineKeyboardButton(text="« Назад", callback_data="profile")]
        ]
    )

# Меню выбора криптовалюты
def get_crypto_currencies_kb(amount):
    # amount передаем, чтобы знать контекст, но в callback_data можно просто asset
    assets = ["USDT", "TON", "BTC", "TRX"]
    buttons = []
    # Делаем по 2 кнопки в ряд
    row = []
    for asset in assets:
        row.append(InlineKeyboardButton(text=f"💎 {asset}", callback_data=f"pay_asset_{asset}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="pay_crypto")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Меню проверки оплаты
def get_payment_check_kb(url, invoice_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Оплатить", url=url)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_pay_{invoice_id}")],
            [InlineKeyboardButton(text="« Отмена", callback_data="profile")]
        ]
    )

# Меню покупки
def get_buy_vpn_kb(price):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Оплатить {price} руб.", callback_data="buy_confirm")],
            [InlineKeyboardButton(text="🏷 Ввести скидочный купон", callback_data="enter_discount")]
        ]
    )

# Меню промокодов
promo_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Активировать промокод на баланс", callback_data="activate_promo")]
    ]
)

# --- АДМИН ПАНЕЛЬ (КНОПКИ) ---

# Главное меню админа
admin_main_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Промо & Скидки", callback_data="adm_promo_cat"), InlineKeyboardButton(text="🔗 Реф. ссылки", callback_data="admin_referrals_cat")],
        [InlineKeyboardButton(text="💎 Подписки", callback_data="adm_subs_cat"), InlineKeyboardButton(text="👤 Юзеры", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="🖥 Пул ключей", callback_data="adm_nodes_cat"), InlineKeyboardButton(text="💾 База/Экспорт", callback_data="adm_db_cat")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast_start"), InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")]
    ]
)

# Категория: Промокоды
admin_promo_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод (Баланс)", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="➕ Создать купон (Скидка)", callback_data="admin_create_discount")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_back_to_main")]
    ]
)

# Категория: Реферальные ссылки
admin_referral_main_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать реф. ссылку", callback_data="admin_create_ref")],
        [InlineKeyboardButton(text="📋 Список всех реф. ссылок", callback_data="admin_list_refs")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_back_to_main")]
    ]
)

def get_referrals_list_kb(refs):
    keyboard = []
    for code, bonus, comment, uses in refs:
        keyboard.append([
            InlineKeyboardButton(text=f"🔗 {code} ({uses} пер.)", callback_data="ignore")
        ])
        keyboard.append([
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"adm_del_ref_{code}")
        ])
    keyboard.append([InlineKeyboardButton(text="« Назад", callback_data="admin_referrals_cat")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Категория: Подписки
admin_subs_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Выдать подписку по ID", callback_data="admin_gift_vpn")],
        [InlineKeyboardButton(text="🗑 Деактивировать подписку по ID", callback_data="admin_clear_vpn")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_back_to_main")]
    ]
)

# Категория: Ключи
admin_servers_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📥 Добавить ключи", callback_data="admin_add_nodes_btn")],
        [InlineKeyboardButton(text="🖥 Управление серверами", callback_data="admin_list_nodes")],
        [InlineKeyboardButton(text="🗑 Очистить пул ключей", callback_data="admin_clear_nodes_btn")],
        [InlineKeyboardButton(text="📊 Статус пула", callback_data="adm_stats_nodes")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_back_to_main")]
    ]
)

def get_nodes_management_kb(nodes, page=0):
    import urllib.parse
    keyboard = []
    page_size = 10
    start = page * page_size
    end = start + page_size
    
    current_nodes = nodes[start:end]
    
    for node_id, node_data, is_active, node_name in current_nodes:
        # Приоритет имени из БД, иначе из ключа
        display_name = node_name if node_name else (node_data.split("#")[-1] if "#" in node_data else f"ID: {node_id}")
        
        # Декодируем URL-encoded строки (если название было закодировано)
        try:
            display_name = urllib.parse.unquote(display_name)
        except:
            pass  # Если не получилось декодировать, оставляем как есть
        
        status_emoji = "✅" if is_active else "❌"
        
        keyboard.append([
            InlineKeyboardButton(text=f"{status_emoji} {display_name[:20]}", callback_data=f"node_toggle_{node_id}_{page}")
        ])
        keyboard.append([
            InlineKeyboardButton(text="✏️ Изм имя", callback_data=f"node_rename_{node_id}"),
            InlineKeyboardButton(text="🔑 Изм ключ", callback_data=f"node_editkey_{node_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"node_delete_{node_id}_{page}")
        ])
    
    # Кнопки навигации
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"nodes_page_{page-1}"))
    if end < len(nodes):
        nav_row.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"nodes_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton(text="« Назад", callback_data="adm_nodes_cat")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_users_list_kb(users):
    keyboard = []
    for user_id, username, balance in users:
        # Убираем None из имени
        name = username if username else f"ID: {user_id}"
        keyboard.append([
            InlineKeyboardButton(text=f"👤 {name} ({balance}р)", callback_data=f"adm_manage_user_{user_id}")
        ])
    keyboard.append([InlineKeyboardButton(text="« Назад", callback_data="admin_back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_user_manage_kb(user_id, has_sub=False, is_active=False):
    
    if not has_sub:
        btn_sub = InlineKeyboardButton(text="➕ Выдать подписку", callback_data=f"adm_gift_sub_{user_id}")
    elif is_active:
        btn_sub = InlineKeyboardButton(text="❌ Отключить подписку", callback_data=f"adm_del_sub_{user_id}")
    else:
        btn_sub = InlineKeyboardButton(text="✅ Включить подписку", callback_data=f"adm_restore_sub_{user_id}")

    keyboard = [
        [btn_sub],
        [InlineKeyboardButton(text="🔄 Сбросить ссылку (UUID)", callback_data=f"adm_reset_uuid_{user_id}")],
        [InlineKeyboardButton(text="📱 Изменить лимит устройств", callback_data=f"adm_limit_user_{user_id}")],
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data=f"adm_balance_user_{user_id}")],
        [InlineKeyboardButton(text="« Назад к списку", callback_data="admin_users_list")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Категория: База Данных
admin_db_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📥 Экспорт Юзеров (SQL)", callback_data="admin_export_users_sql")],
        [InlineKeyboardButton(text="📥 Экспорт Ключей (TXT)", callback_data="admin_export_nodes_txt")],
        [InlineKeyboardButton(text="📱 Экспорт Устройств (JSON)", callback_data="admin_export_devices_json")],
        [InlineKeyboardButton(text="📦 Бэкап всей папки (ZIP)", callback_data="admin_export_data_zip")],
        [InlineKeyboardButton(text="💾 Скачать файл бота (.db)", callback_data="admin_download_db")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_back_to_main")]
    ]
)

# Капча (проверка)
def get_captcha_kb(random_code):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я не робот ✅", callback_data=f"captcha_{random_code}")]
        ]
    )

# Меню активной подписки
def get_active_sub_kb(happ_link=None):
    buttons = []
    if happ_link:
        buttons.append([InlineKeyboardButton(text="🚀 Подключить в Happ", url=happ_link)])
    buttons.append([InlineKeyboardButton(text="🔗 Настройка подключения", callback_data="connection")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Меню подписки
async def get_subscription_menu_kb(short_link=None):
    btns = []

    # Кнопка для открытия TMA (использует Telegram initData для аутентификации)
    btns.append([InlineKeyboardButton(text="⚙️ Управление устройствами", web_app=WebAppInfo(url="https://vpn-cloude-production.up.railway.app/dashboard"))])

    if short_link:
        btns.append([InlineKeyboardButton(text="🚀 Подключить в Happ", url=short_link)])

    btns.append([
        InlineKeyboardButton(text="📱 Клиенты", callback_data="show_clients"),
        InlineKeyboardButton(text="🆘 Помощь", callback_data="help_connection")
    ])
    btns.append([InlineKeyboardButton(text="🔄 Сбросить ссылку", callback_data="reset_link")])
    btns.append([InlineKeyboardButton(text="« Назад в меню", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=btns)

# Меню управления устройствами (кнопки под TMA)
def get_device_action_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить устройство", web_app=WebAppInfo(url="https://vpn-cloude-production.up.railway.app/dashboard"))],
            [InlineKeyboardButton(text="⚙️ Управление устройствами", web_app=WebAppInfo(url="https://vpn-cloude-production.up.railway.app/dashboard"))],
            [InlineKeyboardButton(text="🔄 Сбросить ссылку", callback_data="reset_link")],
            [InlineKeyboardButton(text="🆘 Помощь", callback_data="help_connection")],
            [InlineKeyboardButton(text="« Назад", callback_data="connection")]
        ]
    )


# Меню устройств
def get_devices_kb(devices, limit):
    kb = []
    
    # Список устройств (кнопки для удаления)
    if devices:
        for dev in devices:
            # dev: (id, name, ... ) - примерная структура
            dev_id = dev['id']
            dev_name = dev['name']
            kb.append([InlineKeyboardButton(text=f"📱 {dev_name}", callback_data=f"device_del_{dev_id}")])
    else:
        kb.append([InlineKeyboardButton(text="Список устройств пуст", callback_data="ignore")])

    kb.append([InlineKeyboardButton(text="🗑 Удалить все устройства", callback_data="device_del_all")])
    kb.append([InlineKeyboardButton(text="➕ Добавить устройство", callback_data="device_add")])
    kb.append([InlineKeyboardButton(text="« Назад", callback_data="connection")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Меню клиентов
def get_clients_kb():
    from config import GITHUB_PAGE_URL
    return InlineKeyboardMarkup( 
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Авто-установка (Рекомендуем)", url=f"{GITHUB_PAGE_URL}/client")],
            [InlineKeyboardButton(text="🤖 Android", url="https://play.google.com/store/apps/details?id=com.happproxy"), InlineKeyboardButton(text="🍏 iOS / iPadOS", url="https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973")],
            [InlineKeyboardButton(text="💻 Windows", url="https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe")],
            [InlineKeyboardButton(text="« Назад", callback_data="connection")]
        ]
    )

