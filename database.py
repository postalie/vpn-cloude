import os
import shutil
import aiosqlite
from config import DB_NAME

async def create_tables():
    # Миграция: если старая БД лежит в корне, переносим ее в новую папку
    old_db = "bot_database.db"
    db_dir = os.path.dirname(DB_NAME)
    
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    if os.path.exists(old_db) and not os.path.exists(DB_NAME):
        shutil.move(old_db, DB_NAME)
        print(f"БД перенесена в {DB_NAME}")

    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                is_verified BOOLEAN DEFAULT 0,
                balance INTEGER DEFAULT 0
            )
        ''')
        # Создаем таблицу, если ее нет
        await db.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                sub_uuid TEXT,
                expires_at DATETIME,
                is_active BOOLEAN DEFAULT 1,
                device_limit INTEGER DEFAULT 5
            )
        ''')
        
        # Проверяем структуру таблицы (на случай если она была создана в старой версии)
        # В SQLite ALTER TABLE ADD COLUMN не поддерживает UNIQUE напрямую
        async with db.execute('PRAGMA table_info(subscriptions)') as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
            
        if 'sub_uuid' not in columns:
            print("DB MIGRATION: Adding 'sub_uuid' to subscriptions")
            await db.execute('ALTER TABLE subscriptions ADD COLUMN sub_uuid TEXT')
            # Создаем индекс для уникальности, раз нельзя в ADD COLUMN
            await db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_sub_uuid ON subscriptions(sub_uuid)')
        
        if 'expires_at' not in columns:
            print("DB MIGRATION: Adding 'expires_at' to subscriptions")
            await db.execute('ALTER TABLE subscriptions ADD COLUMN expires_at DATETIME')

        if 'is_active' not in columns:
            await db.execute('ALTER TABLE subscriptions ADD COLUMN is_active BOOLEAN DEFAULT 1')
            
        if 'device_limit' not in columns:
            print("DB MIGRATION: Adding 'device_limit' to subscriptions")
            await db.execute('ALTER TABLE subscriptions ADD COLUMN device_limit INTEGER DEFAULT 5')
            # Обновляем все существующие подписки
            await db.execute('UPDATE subscriptions SET device_limit = 5 WHERE device_limit IS NULL')

        # Таблица промокодов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                amount INTEGER,
                activations INTEGER
            )
        ''')
        # История активаций (чтобы один юзер не вводил дважды)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS logic_activations (
                user_id INTEGER,
                code TEXT,
                UNIQUE(user_id, code)
            )
        ''')
        # Таблица скидочных купонов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS discounts (
                code TEXT PRIMARY KEY,
                percent INTEGER,
                activations INTEGER
            )
        ''')
        # Таблица готовых ключей ("Склад")
        await db.execute('''
            CREATE TABLE IF NOT EXISTS vpn_keys (
                key_id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_data TEXT UNIQUE,
                is_sold BOOLEAN DEFAULT 0
            )
        ''')
        # Таблица серверных нод (ваши общие ключи)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS server_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_data TEXT UNIQUE,
                node_name TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        async with db.execute('PRAGMA table_info(server_nodes)') as cursor:
            node_columns = [row[1] for row in await cursor.fetchall()]
        
        if 'node_name' not in node_columns:
            print("DB MIGRATION: Adding 'node_name' to server_nodes")
            await db.execute('ALTER TABLE server_nodes ADD COLUMN node_name TEXT')

        if 'is_active' not in node_columns:
            print("DB MIGRATION: Adding 'is_active' to server_nodes")
            await db.execute('ALTER TABLE server_nodes ADD COLUMN is_active BOOLEAN DEFAULT 1')

        # Таблица реферальных ссылок (админских)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS referral_links (
                code TEXT PRIMARY KEY,
                bonus_amount INTEGER DEFAULT 0,
                comment TEXT,
                uses INTEGER DEFAULT 0
            )
        ''')

        # Таблица переходов по рефкам
        await db.execute('''
            CREATE TABLE IF NOT EXISTS referral_activations (
                user_id INTEGER PRIMARY KEY,
                code TEXT,
                activated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица уникальных устройств для подписок
        await db.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sub_uuid TEXT,
                device_hash TEXT,
                device_name TEXT,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sub_uuid, device_hash)
            )
        ''')

        async with db.execute('PRAGMA table_info(devices)') as cursor:
            device_columns = [row[1] for row in await cursor.fetchall()]

        # Проверка на наличие id (для старых баз)
        if 'id' not in device_columns:
            print("DB MIGRATION: Recreating 'devices' table with 'id' column")
            await db.execute('''
                CREATE TABLE IF NOT EXISTS devices_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sub_uuid TEXT,
                    device_hash TEXT,
                    device_name TEXT,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(sub_uuid, device_hash)
                )
            ''')
            # Копируем данные если есть
            try:
                await db.execute('''
                    INSERT INTO devices_new (sub_uuid, device_hash, device_name, last_seen)
                    SELECT sub_uuid, device_hash, device_name, last_seen FROM devices
                ''')
            except: pass
            await db.execute('DROP TABLE IF EXISTS devices')
            await db.execute('ALTER TABLE devices_new RENAME TO devices')

        if 'device_name' not in device_columns:
            await db.execute('ALTER TABLE devices ADD COLUMN device_name TEXT')
        if 'last_seen' not in device_columns:
            await db.execute('ALTER TABLE devices ADD COLUMN last_seen DATETIME')
            await db.execute('UPDATE devices SET last_seen = CURRENT_TIMESTAMP')

        # Индекс для ускорения поиска дубликатов
        await db.execute('CREATE INDEX IF NOT EXISTS idx_devices_sub_uuid ON devices(sub_uuid)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_devices_hash ON devices(device_hash)')

        # Таблица обработанных счетов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS processed_invoices (
                invoice_id TEXT PRIMARY KEY,
                user_id INTEGER,
                amount INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица временных токенов для входа на сайт
        await db.execute('''
            CREATE TABLE IF NOT EXISTS web_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        await db.commit()

async def add_user(user_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
        await db.commit()

async def add_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def verify_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET is_verified = 1 WHERE user_id = ?', (user_id,))
        await db.commit()

async def create_promo(code, amount, activations):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO promocodes (code, amount, activations) VALUES (?, ?, ?)', (code, amount, activations))
        await db.commit()

async def activate_promo(user_id, code):
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем промокод
        async with db.execute('SELECT amount, activations FROM promocodes WHERE code = ?', (code,)) as cursor:
            promo = await cursor.fetchone()
        
        if not promo:
            return "not_found"
        
        amount, activations = promo
        if activations <= 0:
            return "ended"

        # Проверяем, активировал ли уже
        async with db.execute('SELECT 1 FROM logic_activations WHERE user_id = ? AND code = ?', (user_id, code)) as cursor:
            if await cursor.fetchone():
                return "already_activated"

        # Активируем
        await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        await db.execute('UPDATE promocodes SET activations = activations - 1 WHERE code = ?', (code,))
        await db.execute('INSERT INTO logic_activations (user_id, code) VALUES (?, ?)', (user_id, code))
        await db.commit()
        return amount

async def create_discount(code, percent, activations):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO discounts (code, percent, activations) VALUES (?, ?, ?)', (code, percent, activations))
        await db.commit()

async def get_discount(code):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT percent, activations FROM discounts WHERE code = ?', (code,)) as cursor:
            return await cursor.fetchone()

async def use_discount(code):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE discounts SET activations = activations - 1 WHERE code = ?', (code,))
        await db.commit()

async def add_subscription(user_id, sub_uuid, days=30):
    from datetime import datetime, timedelta
    expires_at = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO subscriptions (user_id, sub_uuid, expires_at, is_active) 
            VALUES (?, ?, ?, 1)
        ''', (user_id, sub_uuid, expires_at))
        await db.commit()

async def get_subscription(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT sub_uuid FROM subscriptions WHERE user_id = ? AND is_active = 1', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_subscription_by_uuid(sub_uuid):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id, expires_at, is_active, device_limit FROM subscriptions WHERE sub_uuid = ?', (sub_uuid,)) as cursor:
            return await cursor.fetchone()

async def extend_subscription(user_id, days=30):
    from datetime import datetime, timedelta
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT expires_at, sub_uuid FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                expires_at_str, sub_uuid = row
                if expires_at_str:
                    current_expiry = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
                else:
                    current_expiry = datetime.now()
                
                # Продлеваем
                new_expiry = max(current_expiry, datetime.now()) + timedelta(days=days)
                new_expiry_str = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
                
                # Если UUID был None (старый юзер), генерируем новый
                if not sub_uuid:
                    import uuid
                    sub_uuid = str(uuid.uuid4())
                    await db.execute('UPDATE subscriptions SET expires_at = ?, sub_uuid = ?, is_active = 1 WHERE user_id = ?', 
                                     (new_expiry_str, sub_uuid, user_id))
                else:
                    await db.execute('UPDATE subscriptions SET expires_at = ?, is_active = 1 WHERE user_id = ?', 
                                     (new_expiry_str, user_id))
                await db.commit()
                return True
            return False

async def get_subscription_info(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT sub_uuid, expires_at, is_active, device_limit FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def set_device_limit(user_id, limit):
    """Устанавливает лимит устройств для пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE subscriptions SET device_limit = ? WHERE user_id = ?', (limit, user_id))
        await db.commit()

async def delete_subscription(user_id):
    """Деактивирует подписку пользователя (is_active = 0) вместо удаления"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE subscriptions SET is_active = 0 WHERE user_id = ?', (user_id,))
        await db.commit()

async def activate_subscription(user_id):
    """Активирует подписку пользователя (is_active = 1)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE subscriptions SET is_active = 1 WHERE user_id = ?', (user_id,))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id, username, balance FROM users') as cursor:
            return await cursor.fetchall()
            
async def get_all_users_ids():
    """Возвращает список ID всех пользователей для рассылки"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
             # fetchall возвращает список кортежей [(id1,), (id2,), ...]
             # преобразуем в плоский список [id1, id2, ...]
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def decrease_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
         # Проверяем баланс
        async with db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < amount:
                return False
        
        await db.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
        await db.commit()
        return True

async def add_key_to_stock(key_data):
    """Добавляет один ключ в базу"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO vpn_keys (key_data, is_sold) VALUES (?, 0)', (key_data,))
        await db.commit()

async def get_free_key_from_stock():
    """Берет один свободный ключ и помечает его проданным"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT key_id, key_data FROM vpn_keys WHERE is_sold = 0 LIMIT 1') as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            key_id, key_data = row
            # Помечаем как проданный
            await db.execute('UPDATE vpn_keys SET is_sold = 1 WHERE key_id = ?', (key_id,))
            await db.commit()
            return key_data

async def get_keys_count():
    """Возвращает количество свободных ключей"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM vpn_keys WHERE is_sold = 0') as cursor:
            return (await cursor.fetchone())[0]

async def add_server_node(node_data):
    """Добавляет общий ключ (ноду) в базу"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO server_nodes (node_data) VALUES (?)', (node_data,))
        await db.commit()

async def get_all_server_nodes(only_active=True):
    """Возвращает список всех общих ключей (по умолчанию только активные)"""
    async with aiosqlite.connect(DB_NAME) as db:
        query = 'SELECT node_data, node_name FROM server_nodes'
        if only_active:
            query += ' WHERE is_active = 1'
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return rows # Возвращаем список кортежей (data, name)

async def get_all_server_nodes_admin():
    """Возвращает все данные нод для админки"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT id, node_data, is_active, node_name FROM server_nodes') as cursor:
            return await cursor.fetchall()

async def edit_node_name(node_id, new_name):
    """Меняет название (локацию) ноды"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE server_nodes SET node_name = ? WHERE id = ?', (new_name, node_id))
        await db.commit()

async def edit_node_data(node_id, new_data):
    """Меняет сам ключ (vless/vmess) ноды"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE server_nodes SET node_data = ? WHERE id = ?', (new_data, node_id))
        await db.commit()

async def toggle_node_status(node_id):
    """Переключает статус активности ноды"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT is_active FROM server_nodes WHERE id = ?', (node_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                new_status = 0 if row[0] else 1
                await db.execute('UPDATE server_nodes SET is_active = ? WHERE id = ?', (new_status, node_id))
                await db.commit()
                return True
            return False

async def delete_node_by_id(node_id):
    """Удаляет ноду по ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM server_nodes WHERE id = ?', (node_id,))
        await db.commit()

async def clear_server_nodes():
    """Очищает список нод"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM server_nodes')
        await db.commit()

async def get_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            users_count = await cursor.fetchone()
        return users_count[0]

async def set_balance(user_id, amount):
    """Устанавливает баланс пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET balance = ? WHERE user_id = ?', (amount, user_id))
        await db.commit()

async def update_balance(user_id, amount):
    """Добавляет сумму к текущему балансу (или отнимает, если amount < 0)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        await db.commit()

async def is_invoice_processed(invoice_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT 1 FROM processed_invoices WHERE invoice_id = ?', (invoice_id,)) as cursor:
            return await cursor.fetchone() is not None

async def add_invoice_processed(invoice_id, user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO processed_invoices (invoice_id, user_id, amount) VALUES (?, ?, ?)', 
                         (invoice_id, user_id, amount))
        await db.commit()

async def reset_subscription_uuid(user_id):
    """Сбрасывает UUID подписки и генерирует новый, также очищает привязанные устройства"""
    import uuid
    import json
    new_uuid = str(uuid.uuid4())
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Получаем старый UUID перед сбросом
        async with db.execute('SELECT sub_uuid FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                old_uuid = row[0]
                if old_uuid:
                    # 2. Удаляем устройства из БД
                    await db.execute('DELETE FROM devices WHERE sub_uuid = ?', (old_uuid,))
                    
                    # 3. Пытаемся очистить кеш в PHP (devices.json), если он на том же сервере
                    try:
                        # Путь к файлу относительно корня проекта
                        json_path = os.path.join(os.getcwd(), 'web', 'devices.json')
                        if os.path.exists(json_path):
                            with open(json_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            if old_uuid in data:
                                del data[old_uuid]
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(data, f)
                    except Exception as e:
                        print(f"Note: Could not clear PHP JSON cache: {e}")

        # 4. Обновляем UUID в базе (только если есть активная подписка)
        await db.execute('UPDATE subscriptions SET sub_uuid = ? WHERE user_id = ? AND is_active = 1', (new_uuid, user_id))
        await db.commit()
    return new_uuid

async def register_device(sub_uuid, device_hash, device_model: str = None):
    """
    Регистрирует новое устройство для UUID.
    Возвращает: (success, current_count, limit, user_id, is_new)
    
    Args:
        sub_uuid: UUID подписки
        device_hash: Хеш устройства (model|platform)
        device_model: Название модели устройства для авто-переименования
    """
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем лимит и user_id
        async with db.execute('SELECT user_id, device_limit FROM subscriptions WHERE sub_uuid = ?', (sub_uuid,)) as cursor:
            sub = await cursor.fetchone()
            if not sub:
                print(f"DEBUG DB: No subscription found for UUID {sub_uuid}")
                return False, 0, 0, None

            user_id, limit = sub
            print(f"DEBUG DB: Found sub for User {user_id}, Limit {limit}")

        # Проверяем, зарегистрировано ли уже это устройство
        async with db.execute('SELECT 1 FROM devices WHERE sub_uuid = ? AND device_hash = ?', (sub_uuid, device_hash)) as cursor:
            if await cursor.fetchone():
                # Обновляем время активности
                await db.execute('UPDATE devices SET last_seen = CURRENT_TIMESTAMP WHERE sub_uuid = ? AND device_hash = ?', (sub_uuid, device_hash))
                await db.commit()
                # Уже есть, получаем общее кол-во
                async with db.execute('SELECT COUNT(*) FROM devices WHERE sub_uuid = ?', (sub_uuid,)) as cursor:
                    count = (await cursor.fetchone())[0]
                return True, count, limit, user_id, False # success, count, limit, user_id, is_new

        # Новое устройство, проверяем лимит
        async with db.execute('SELECT COUNT(*) FROM devices WHERE sub_uuid = ?', (sub_uuid,)) as cursor:
            current_count = (await cursor.fetchone())[0]

        if current_count >= limit:
            return False, current_count, limit, user_id, False

        # Авто-переименование: если модель не "Unknown Device", используем её как имя
        device_name = "Новое устройство"
        if device_model and device_model != "Unknown Device":
            # Очищаем имя от лишних символов
            import re
            # Оставляем только буквы, цифры, /, -, _, пробелы
            clean_model = re.sub(r'[^\w\s/\-_.]', '', device_model).strip()
            if clean_model:
                device_name = clean_model

        # Регистрируем
        await db.execute('INSERT INTO devices (sub_uuid, device_hash, device_name, last_seen) VALUES (?, ?, ?, CURRENT_TIMESTAMP)', 
                        (sub_uuid, device_hash, device_name))
        await db.commit()
        return True, current_count + 1, limit, user_id, True # is_new = True

async def cleanup_duplicate_devices(sub_uuid, device_hash):
    """
    Очищает дубликаты устройств для одного UUID.
    Оставляет только одно устройство с данным device_hash (последнее по last_seen).
    """
    async with aiosqlite.connect(DB_NAME) as db:
        # Находим все устройства с таким device_hash для данного sub_uuid
        async with db.execute('''
            SELECT rowid FROM devices
            WHERE sub_uuid = ? AND device_hash = ?
            ORDER BY last_seen DESC
        ''', (sub_uuid, device_hash)) as cursor:
            rows = await cursor.fetchall()

        # Если больше одного устройства - удаляем дубликаты (оставляем первое)
        if len(rows) > 1:
            for row in rows[1:]:
                await db.execute('DELETE FROM devices WHERE rowid = ?', (row[0],))
            await db.commit()
            print(f"DEBUG DB: Cleaned up {len(rows) - 1} duplicate devices for {sub_uuid}")

async def clear_devices_by_uuid(sub_uuid):
    """Очищает список устройств для UUID"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM devices WHERE sub_uuid = ?', (sub_uuid,))
        await db.commit()

async def get_device_count(user_id):
    """Возвращает текущее количество привязанных устройств пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT sub_uuid FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or not row[0]:
                return 0
            sub_uuid = row[0]
        
        async with db.execute('SELECT COUNT(*) FROM devices WHERE sub_uuid = ?', (sub_uuid,)) as cursor:
            return (await cursor.fetchone())[0]

async def get_user_devices(user_id):
    """Возвращает список всех устройств пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT sub_uuid FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or not row[0]:
                return []
            sub_uuid = row[0]
            
        async with db.execute('SELECT id, device_hash, device_name, last_seen FROM devices WHERE sub_uuid = ?', (sub_uuid,)) as cursor:
            return await cursor.fetchall()

async def rename_device(device_id, new_name):
    """Переименовывает устройство"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE devices SET device_name = ? WHERE id = ?', (new_name, device_id))
        await db.commit()

async def delete_device(device_id):
    """Удаляет устройство"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM devices WHERE id = ?', (device_id,))
        await db.commit()

# --- РЕФЕРАЛЬНАЯ СИСТЕМА ---

async def create_referral_link(code, bonus, comment):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO referral_links (code, bonus_amount, comment) VALUES (?, ?, ?)', (code, bonus, comment))
        await db.commit()

async def get_all_referral_links():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT code, bonus_amount, comment, uses FROM referral_links') as cursor:
            return await cursor.fetchall()

async def delete_referral_link(code):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM referral_links WHERE code = ?', (code,))
        await db.commit()

async def get_referral_link(code):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT bonus_amount, comment FROM referral_links WHERE code = ?', (code,)) as cursor:
            return await cursor.fetchone()

async def add_referral_activation(user_id, code):
    """Регистрирует переход нового пользователя по рефке"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем, не был ли юзер уже кем-то приглашен
        async with db.execute('SELECT 1 FROM referral_activations WHERE user_id = ?', (user_id,)) as cursor:
            if await cursor.fetchone():
                return False
        
        # Записываем активацию
        await db.execute('INSERT INTO referral_activations (user_id, code) VALUES (?, ?)', (user_id, code))
        # Увеличиваем счетчик на рефке
        await db.execute('UPDATE referral_links SET uses = uses + 1 WHERE code = ?', (code,))
        await db.commit()
        return True
        
# --- WEB AUTH TOKENS ---

async def create_web_token(user_id):
    """Создает новый токен для входа на сайт (удаляет старые токены этого юзера)"""
    import secrets
    token = secrets.token_urlsafe(32)
    async with aiosqlite.connect(DB_NAME) as db:
        # Опционально: удаляем старые токены юзера, чтобы работал только последний
        await db.execute('DELETE FROM web_tokens WHERE user_id = ?', (user_id,))
        await db.execute('INSERT INTO web_tokens (token, user_id) VALUES (?, ?)', (token, user_id))
        await db.commit()
    return token

async def get_user_by_token(token):
    """Возвращает user_id по токену и удаляет его (одноразовость) или проверяет по времени"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем токен (токен живет 24 часа)
        async with db.execute('''
            SELECT user_id FROM web_tokens 
            WHERE token = ? AND created_at > datetime('now', '-1 day')
        ''', (token,)) as cursor:
            row = await cursor.fetchone()
            if row:
                user_id = row[0]
                # Если хотим именно ОДНОРАЗОВЫЙ - удаляем. 
                # Но для удобства входа лучше оставить или удалять после обмена на сессию.
                # Оставим пока 24-часовой многоразовый для простоты.
                return user_id
            return None
