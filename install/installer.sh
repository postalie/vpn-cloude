#!/bin/bash

# Скрипт установки и запуска VPN Cloud Bot на Debian 11
# Запуск: bash installer.sh

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
apt install -y python3 python3-pip python3-venv curl net-tools openssl certbot

# Директория проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/vpn-cloude"

echo "📁 Копирование проекта в $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
cp -r "$PROJECT_DIR"/.* "$INSTALL_DIR/" 2>/dev/null || true
cd "$INSTALL_DIR"

# Виртуальное окружение
echo "🐍 Создание venv..."
python3 -m venv venv
source venv/bin/activate

# Зависимости
echo "📚 Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# SSL сертификат для msk.cloudevpn.cfd
DOMAIN="msk.cloudevpn.cfd"
SSL_DIR="$INSTALL_DIR/ssl"
mkdir -p "$SSL_DIR"

echo ""
echo "🔐 Получение SSL-сертификата от Let's Encrypt для $DOMAIN..."

# Останавливаем старые процессы
echo "🛑 Остановка старых процессов..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python.*web_static" 2>/dev/null || true

# Получаем сертификат через standalone режим
certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --email admin@cloudevpn.cfd || {
    echo "❌ Не удалось получить сертификат Let's Encrypt"
    echo ""
    echo "Проверь:"
    echo "  1. Домен $DOMAIN указывает на IP этого сервера"
    echo "  2. Порт 80 открыт: ufw allow 80"
    echo ""
    echo "Пробуем самоподписанный сертификат..."
    DOMAIN=""
}

if [ -n "$DOMAIN" ] && [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    # Копируем сертификаты Let's Encrypt
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/server.crt"
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/server.key"
    chmod 600 "$SSL_DIR/server.key"
    chmod 644 "$SSL_DIR/server.crt"
    echo "✅ Сертификат Let's Encrypt установлен для $DOMAIN!"
else
    # Самоподписанный если не получилось
    echo "🔐 Генерация самоподписанного SSL-сертификата..."
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/server.key" \
        -out "$SSL_DIR/server.crt" \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=Cloude VPN/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:$SERVER_IP,DNS:$DOMAIN"
    
    chmod 600 "$SSL_DIR/server.key"
    chmod 644 "$SSL_DIR/server.crt"
    echo "⚠️  Самоподписанный сертификат"
fi

echo "✅ SSL-сертификат в $SSL_DIR"

# Создание скриптов запуска
echo "🔧 Создание скриптов запуска..."

# Скрипт запуска основного бота (порт 8080)
cat > "$INSTALL_DIR/start_bot.sh" << 'EOF'
#!/bin/bash
cd /opt/vpn-cloude
source venv/bin/activate
nohup python main.py > main.log 2>&1 &
echo $! > /opt/vpn-cloude/bot.pid
echo "Бот запущен с PID: $(cat /opt/vpn-cloude/bot.pid)"
EOF
chmod +x "$INSTALL_DIR/start_bot.sh"

# Скрипт запуска веб-сервера (порт 25666)
cat > "$INSTALL_DIR/start_web.sh" << 'EOF'
#!/bin/bash
cd /opt/vpn-cloude
source venv/bin/activate
nohup python web_static_server.py > web_static.log 2>&1 &
echo $! > /opt/vpn-cloude/web_static.pid
echo "Web сервер запущен с PID: $(cat /opt/vpn-cloude/web_static.pid)"
EOF
chmod +x "$INSTALL_DIR/start_web.sh"

# Скрипт запуска всего
cat > "$INSTALL_DIR/start_all.sh" << 'EOF'
#!/bin/bash
cd /opt/vpn-cloude
bash start_bot.sh
bash start_web.sh
echo "✅ Все сервисы запущены"
EOF
chmod +x "$INSTALL_DIR/start_all.sh"

# Скрипт остановки всего
cat > "$INSTALL_DIR/stop_all.sh" << 'EOF'
#!/bin/bash
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python.*web_static" 2>/dev/null || true
rm -f /opt/vpn-cloude/*.pid
echo "✅ Все сервисы остановлены"
EOF
chmod +x "$INSTALL_DIR/stop_all.sh"

# Запуск бота через nohup
echo "🚀 Запуск основного бота (порт 8080)..."
cd "$INSTALL_DIR"
source venv/bin/activate
nohup python main.py > main.log 2>&1 &
echo $! > "$INSTALL_DIR/bot.pid"

sleep 2

# Запуск веб-сервера через nohup
echo "🚀 Запуск веб-сервера (порт 25666)..."
nohup python web_static_server.py > web_static.log 2>&1 &
echo $! > "$INSTALL_DIR/web_static.pid"

sleep 2

# Проверка что процессы запущены
echo ""
if ps -p $(cat "$INSTALL_DIR/bot.pid") > /dev/null 2>&1; then
    echo "✅ Бот запущен (PID: $(cat "$INSTALL_DIR/bot.pid"))"
else
    echo "❌ Ошибка! Бот не запустился."
    echo "Проверь логи: tail -n 50 $INSTALL_DIR/main.log"
    exit 1
fi

if ps -p $(cat "$INSTALL_DIR/web_static.pid") > /dev/null 2>&1; then
    echo "✅ Web сервер запущен (PID: $(cat "$INSTALL_DIR/web_static.pid"))"
else
    echo "❌ Ошибка! Web сервер не запустился."
    echo "Проверь логи: tail -n 50 $INSTALL_DIR/web_static.log"
    exit 1
fi

echo ""
echo "✅ Готово! Все сервисы запущены"
echo ""
echo "🌐 Сервисы доступны:"
echo "   - Бот + API: https://$DOMAIN:8080"
echo "   - TMA Dashboard: https://$DOMAIN:25666/dashboard"
echo "   - Подписки: https://$DOMAIN:25666/sub/{uuid}"
echo ""
if [ -f "$SSL_DIR/server.crt" ] && [ -n "$DOMAIN" ]; then
    echo "✅ Сертификат доверенный (Let's Encrypt)"
fi
echo ""
echo "📋 Команды:"
echo "   - Логи бота: tail -f $INSTALL_DIR/main.log"
echo "   - Логи веб: tail -f $INSTALL_DIR/web_static.log"
echo "   - Остановить: bash $INSTALL_DIR/stop_all.sh"
echo "   - Запустить: bash $INSTALL_DIR/start_all.sh"
echo "   - Статус: ps aux | grep 'python.*'"
