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

cd "$PROJECT_DIR"

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
SSL_DIR="$PROJECT_DIR/ssl"
mkdir -p "$SSL_DIR"

echo ""
echo "🔐 Получение SSL-сертификата от Let's Encrypt для $DOMAIN..."

# Останавливаем старый процесс
echo "🛑 Остановка старого процесса..."
pkill -f "python.*main.py" 2>/dev/null || true

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
    
    # Скрипт автообновления
    cat > /etc/cron.daily/certbot-renew << 'EOF'
#!/bin/bash
certbot renew --quiet
pkill -f "python.*main.py" 2>/dev/null || true
sleep 2
cd /opt/vpn-cloude && source venv/bin/activate && nohup python main.py > main.log 2>&1 &
EOF
    chmod +x /etc/cron.daily/certbot-renew
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

# Создание скрипта запуска
echo "🔧 Создание скрипта запуска..."
cat > "$PROJECT_DIR/start_bot.sh" << 'EOF'
#!/bin/bash
cd /opt/vpn-cloude
source venv/bin/activate
nohup python main.py > main.log 2>&1 &
echo $! > /opt/vpn-cloude/bot.pid
echo "Бот запущен с PID: $(cat /opt/vpn-cloude/bot.pid)"
EOF
chmod +x "$PROJECT_DIR/start_bot.sh"

# Запуск бота через nohup
echo "🚀 Запуск бота через nohup..."
cd "$PROJECT_DIR"
source venv/bin/activate
nohup python main.py > main.log 2>&1 &
echo $! > "$PROJECT_DIR/bot.pid"

sleep 3

# Проверка что процесс запущен
if ps -p $(cat "$PROJECT_DIR/bot.pid") > /dev/null 2>&1; then
    echo ""
    echo "✅ Готово! Бот запущен в фоне (PID: $(cat "$PROJECT_DIR/bot.pid"))"
    echo ""
    echo "🌐 HTTPS доступен:"
    echo "   - https://$DOMAIN:8080/dashboard"
    echo "   - https://$DOMAIN:8080/health"
    echo ""
    if [ -f "$SSL_DIR/server.crt" ] && [ -n "$DOMAIN" ]; then
        echo "✅ Сертификат доверенный (Let's Encrypt) - браузеры не будут жаловаться!"
    fi
    echo ""
    echo "📋 Команды:"
    echo "   - Логи (realtime): tail -f $PROJECT_DIR/main.log"
    echo "   - Логи (последние 50 строк): tail -n 50 $PROJECT_DIR/main.log"
    echo "   - Остановить: pkill -f 'python.*main.py'"
    echo "   - Статус: ps aux | grep 'python.*main.py'"
    echo "   - Перезапустить: bash $PROJECT_DIR/start_bot.sh"
    echo ""
else
    echo ""
    echo "❌ Ошибка! Бот не запустился."
    echo "Проверь логи: tail -n 50 $PROJECT_DIR/main.log"
    exit 1
fi
