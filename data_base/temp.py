import sqlite3
import os

# Путь к твоему дампу и будущей базе
SQL_FILE = 'data_base/database_dump.sql'
DB_FILE = 'bot_database.db'

def build_db():
    if not os.path.exists(SQL_FILE):
        print(f"Ошибка: Файл {SQL_FILE} не найден!")
        return

    try:
        # Читаем SQL-команды из текста
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # Создаем базу и выполняем скрипт
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()

        print(f"✅ Готово! Файл {DB_FILE} создан и наполнен данными.")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")

if __name__ == "__main__":
    build_db()