#!/bin/bash

# Скрипт установки и запуска VPN Cloud Bot на Debian 11
# Запуск: bash install.sh

set -e

echo "🚀 Начало установки..."

# Фикс для Debian 11 (bullseye) - репозитории перемещены в archive
echo "🔧 Фикс репозиториев..."
sed -i 's|http://deb.debian.org/debian bullseye|http://archive.debian.org/debian bullseye|g' /etc/apt/sources.list
sed -i 's|http://security.debian.org bullseye-security|http://archive.debian.org/debian-security bullseye-security|g' /etc/apt/sources.list
sed -i '/bullseye-backports/d' /etc/apt/sources.list

# Обновление и установка пакетов
echo "📦 Обновление и установка пакетов..."
apt update
apt install -y python3 python3-pip python3-venv screen curl net-tools

# Директория проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Виртуальное окружени
echo "🐍 Создание venv.."
python3 -m venv venv
source venv/bin/activate

# Зависимости
echo "📚 Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Остановка старого процесса если есть
echo "🛑 Остановка старого процесса.."
pkill -f "python.*main.py" 2>/dev/null || true
screen -S vpn-cloude -X quit 2>/dev/null || true

# Запуск в screen (работает после отключения SSH)
echo "🚀 Запуск бота в screen..."
screen -dmS vpn-cloude bash -c "cd $PROJECT_DIR && source venv/bin/activate && python main.py"

sleep 2

echo ""
echo "✅ Готово! Бот запущен в screen-сессии 'vpn-cloude'"
echo ""
echo "📋 Команды:"
echo "   - Подключиться: screen -r vpn-cloude"
echo "   - Отцепиться: Ctrl+A, затем D"
echo "   - Логи: screen -r vpn-cloude"
echo "   - Остановить: screen -S vpn-cloude -X quit"
