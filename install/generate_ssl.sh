#!/bin/bash

# Генерация самоподписанного SSL-сертификата для VPN Cloud Bot

CERT_DIR="/opt/vpn-cloude/ssl"
mkdir -p "$CERT_DIR"

echo "🔐 Генерация SSL-сертификата..."

# Генерация приватного ключа и сертификата
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=Cloude VPN/CN=cloudevpn.local" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:$(hostname -I | awk '{print $1}')"

chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.crt"

echo ""
echo "✅ Сертификат создан:"
echo "   - Ключ: $CERT_DIR/server.key"
echo "   - Сертификат: $CERT_DIR/server.crt"
echo ""
echo "⚠️  Самоподписанный сертификат - браузеры будут показывать предупреждение."
echo "   Для продакшена используй Let's Encrypt:"
echo "   apt install certbot"
echo "   certbot certonly --standalone -d ваш-домен.ru"
