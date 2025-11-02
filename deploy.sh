#!/bin/bash
# Скрипт для быстрого развертывания на Ubuntu сервере
# Использование: bash deploy.sh

set -e  # Остановка при ошибке

echo "🚀 Начало развертывания Yandex Music → Spotify Transfer App"
echo ""

# Проверка прав root/sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Запустите скрипт с sudo: sudo bash deploy.sh"
    exit 1
fi

# Переменные
APP_DIR="/opt/tys"
APP_USER="www-data"
APP_SERVICE="tys"

echo "📦 Шаг 1: Установка зависимостей системы..."
apt update
apt install -y python3.12 python3.12-venv python3-pip python3-dev
apt install -y build-essential nginx certbot python3-certbot-nginx

echo ""
echo "📁 Шаг 2: Подготовка директории..."
mkdir -p $APP_DIR
chown -R $APP_USER:$APP_USER $APP_DIR

echo ""
echo "⚠️  Шаг 3: Загрузка проекта"
echo "Скопируйте файлы проекта в $APP_DIR"
echo "Нажмите Enter когда файлы будут скопированы..."
read

cd $APP_DIR

echo ""
echo "🐍 Шаг 4: Создание виртуального окружения..."
if [ ! -d "venv" ]; then
    python3.12 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "⚙️  Шаг 5: Настройка .env файла..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        cat > .env << EOF
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=https://tys.flurisrv.ru/callback/spotify
APP_URL=https://tys.flurisrv.ru
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
LOG_LEVEL=INFO
EOF
    fi
    echo "📝 Откройте файл .env и заполните необходимые поля:"
    echo "   nano $APP_DIR/.env"
    echo ""
    echo "Нажмите Enter когда .env будет настроен..."
    read
fi

chmod 600 .env
chown $APP_USER:$APP_USER .env

echo ""
echo "🌐 Шаг 6: Настройка Nginx..."
cat > /etc/nginx/sites-available/$APP_SERVICE << 'NGINX_CONFIG'
server {
    listen 80;
    server_name tys.flurisrv.ru;

    access_log /var/log/nginx/tys_access.log;
    error_log /var/log/nginx/tys_error.log;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
NGINX_CONFIG

ln -sf /etc/nginx/sites-available/$APP_SERVICE /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

echo ""
echo "🔒 Шаг 7: Настройка SSL..."
echo "Запустите certbot для получения SSL сертификата:"
echo "  certbot --nginx -d tys.flurisrv.ru"
echo ""
echo "Нажмите Enter чтобы продолжить (пропустить SSL на потом)..."
read

echo ""
echo "🔄 Шаг 8: Создание systemd service..."
cat > /etc/systemd/system/$APP_SERVICE.service << SERVICE_CONFIG
[Unit]
Description=Yandex Music to Spotify Transfer App
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$APP_SERVICE
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICE_CONFIG

chown -R $APP_USER:$APP_USER $APP_DIR

systemctl daemon-reload
systemctl enable $APP_SERVICE
systemctl start $APP_SERVICE

echo ""
echo "✅ Развертывание завершено!"
echo ""
echo "Проверьте статус:"
echo "  sudo systemctl status $APP_SERVICE"
echo ""
echo "Просмотр логов:"
echo "  sudo journalctl -u $APP_SERVICE -f"
echo ""
echo "⚠️  Не забудьте:"
echo "  1. Настроить SSL: certbot --nginx -d tys.flurisrv.ru"
echo "  2. Добавить Redirect URI в Spotify Dashboard: https://tys.flurisrv.ru/callback/spotify"
echo ""
echo "🎉 Готово!"

