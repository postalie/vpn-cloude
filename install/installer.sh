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
apt install -y python3 python3-pip python3-venv curl net-tools openssl certbot dnsutils

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

# Убиваем все старые процессы бота и освобождаем порты
echo "🛑 Остановка старых процессов..."
pkill -9 -f "python.*main.py" 2>/dev/null || true
fuser -k 8080/tcp 2>/dev/null || true
fuser -k 80/tcp 2>/dev/null || true

# Ждём пока порты точно освободятся
echo "⏳ Ожидание освобождения портов..."
for i in $(seq 1 15); do
    PORT_8080=$(ss -tlnp | grep ':8080 ' || true)
    PORT_80=$(ss -tlnp | grep ':80 ' || true)
    if [ -z "$PORT_8080" ] && [ -z "$PORT_80" ]; then
        echo "✅ Порты 80 и 8080 свободны"
        break
    fi
    echo "⏳ Ждём... ($i/15)"
    sleep 1
done

# SSL сертификат
DOMAIN="msk.cloudevpn.cfd"
SSL_DIR="$PROJECT_DIR/ssl"
mkdir -p "$SSL_DIR"

echo ""
echo "🔐 Получение SSL-сертификата от Let's Encrypt для $DOMAIN..."

# Получаем внешний IP сервера
echo "🔍 Определение внешнего IP сервера..."
SERVER_IP=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || \
            curl -s --max-time 5 https://ifconfig.me 2>/dev/null || \
            curl -s --max-time 5 https://icanhazip.com 2>/dev/null || \
            echo "")

if [ -z "$SERVER_IP" ]; then
    echo "⚠️  Не удалось определить внешний IP"
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo "⚠️  Используем локальный IP: $SERVER_IP"
else
    echo "✅ Внешний IP сервера: $SERVER_IP"
fi

# Проверяем DNS резолвинг домена
echo "🔍 Проверка DNS для $DOMAIN..."
DOMAIN_IP=$(dig +short "$DOMAIN" 2>/dev/null | tail -1 || \
            host "$DOMAIN" 2>/dev/null | awk '/has address/ {print $4}' | head -1 || \
            echo "")

CERT_OK=false

if [ "$DOMAIN_IP" = "$SERVER_IP" ]; then
    echo "✅ DNS корректен: $DOMAIN -> $SERVER_IP"

    # Получаем сертификат через standalone режим
    if certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --email admin@cloudevpn.cfd; then
        if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
            cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/server.crt"
            cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/server.key"
            chmod 600 "$SSL_DIR/server.key"
            chmod 644 "$SSL_DIR/server.crt"
            echo "✅ Сертификат Let's Encrypt установлен!"
            CERT_OK=true

            # Скрипт автообновления через cron
            cat > /etc/cron.daily/certbot-renew << CRONEOF
#!/bin/bash
certbot renew --quiet --deploy-hook "cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $SSL_DIR/server.crt && cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $SSL_DIR/server.key && chmod 600 $SSL_DIR/server.key && pkill -9 -f 'python.*main.py' 2>/dev/null || true && sleep 3 && bash $PROJECT_DIR/start_bot.sh"
CRONEOF
            chmod +x /etc/cron.daily/certbot-renew
            echo "✅ Автообновление сертификата настроено"
        fi
    else
        echo "❌ Certbot завершился с ошибкой"
    fi
else
    if [ -z "$DOMAIN_IP" ]; then
        echo "⚠️  DNS для $DOMAIN не резолвится"
    else
        echo "⚠️  DNS не совпадает: $DOMAIN -> $DOMAIN_IP (сервер: $SERVER_IP)"
    fi
fi

# Если Let's Encrypt не получилось — самоподписанный
if [ "$CERT_OK" = false ]; then
    echo ""
    echo "🔐 Генерация самоподписанного SSL-сертификата..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/server.key" \
        -out "$SSL_DIR/server.crt" \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=Cloude VPN/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:$SERVER_IP,DNS:$DOMAIN"

    chmod 600 "$SSL_DIR/server.key"
    chmod 644 "$SSL_DIR/server.crt"
    echo "⚠️  Используется самоподписанный сертификат"
fi

echo "✅ SSL-сертификат сохранён в $SSL_DIR"

# Создание скрипта запуска
echo "🔧 Создание скрипта запуска..."
cat > "$PROJECT_DIR/start_bot.sh" << EOF
#!/bin/bash
cd "$PROJECT_DIR"
source venv/bin/activate

echo "🛑 Останавливаем старые процессы..."
pkill -9 -f "python.*main.py" 2>/dev/null || true
fuser -k 8080/tcp 2>/dev/null || true

# Ждём пока порт 8080 точно освободится
for i in \$(seq 1 15); do
    if ! ss -tlnp | grep -q ':8080 '; then
        echo "✅ Порт 8080 свободен"
        break
    fi
    echo "⏳ Ждём освобождения порта 8080... (\$i/15)"
    sleep 1
done

# Финальная проверка
if ss -tlnp | grep -q ':8080 '; then
    echo "❌ Порт 8080 всё ещё занят! Прерываем запуск."
    exit 1
fi

nohup python main.py > "$PROJECT_DIR/main.log" 2>&1 &
BOT_PID=\$!
echo \$BOT_PID > "$PROJECT_DIR/bot.pid"
echo "✅ Бот запущен с PID: \$BOT_PID"
EOF
chmod +x "$PROJECT_DIR/start_bot.sh"

# Запуск бота
echo "🚀 Запуск бота..."
bash "$PROJECT_DIR/start_bot.sh"

# Ждём дольше чтобы бот успел инициализироваться
sleep 5

# Проверка что процесс запущен
BOT_PID=$(cat "$PROJECT_DIR/bot.pid" 2>/dev/null || echo "")

if [ -n "$BOT_PID" ] && ps -p "$BOT_PID" > /dev/null 2>&1; then
    echo ""
    echo "✅ Готово! Бот запущен в фоне (PID: $BOT_PID)"
    echo ""
    echo "🌐 HTTPS доступен:"
    echo "   - https://$DOMAIN:8080/dashboard"
    echo "   - https://$DOMAIN:8080/health"
    echo ""
    if [ "$CERT_OK" = true ]; then
        echo "✅ Сертификат доверенный (Let's Encrypt) - браузеры не будут жаловаться!"
    else
        echo "⚠️  Самоподписанный сертификат - браузеры будут предупреждать"
    fi
    echo ""
    echo "📋 Команды:"
    echo "   - Логи (realtime):           tail -f $PROJECT_DIR/main.log"
    echo "   - Логи (последние 50 строк): tail -n 50 $PROJECT_DIR/main.log"
    echo "   - Остановить:                pkill -f 'python.*main.py'"
    echo "   - Статус:                    ps aux | grep 'python.*main.py'"
    echo "   - Перезапустить:             bash $PROJECT_DIR/start_bot.sh"
    echo ""
else
    echo ""
    echo "❌ Ошибка! Бот не запустился."
    echo "Последние строки лога:"
    echo "---"
    cat "$PROJECT_DIR/main.log" 2>/dev/null | tail -n 30
    echo "---"
    exit 1
fi