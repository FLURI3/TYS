# Инструкция по развертыванию на Ubuntu сервере

Полная инструкция по развертыванию приложения на Ubuntu сервере с доменом `tys.flurisrv.ru`.

## 📋 Предварительные требования

- Ubuntu 20.04+ (или другая Debian-based система)
- Доступ к серверу по SSH с правами sudo
- Настроенный DNS для домена `tys.flurisrv.ru` (A-запись указывает на IP вашего сервера)
- Открытые порты 80 и 443 (для HTTP/HTTPS)

## 🚀 Шаг 1: Подготовка сервера

### 1.1 Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
```

### 1.2 Установка Python и зависимостей

```bash
sudo apt install -y python3.12 python3.12-venv python3-pip python3-dev
sudo apt install -y build-essential nginx certbot python3-certbot-nginx
```

**Примечание:** Если Python 3.12 недоступен в репозиториях, добавьте deadsnakes PPA:
```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

### 1.3 Настройка firewall (если используется UFW)

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## 📦 Шаг 2: Загрузка проекта на сервер

### 2.1 Клонирование репозитория (если проект в Git)

```bash
cd /opt
sudo git clone <ваш_репозиторий> tys
sudo chown -R $USER:$USER /opt/tys
cd /opt/tys
```

### 2.2 Или загрузка файлов вручную

```bash
# Создайте директорию для проекта
sudo mkdir -p /opt/tys
sudo chown -R $USER:$USER /opt/tys

# Загрузите файлы через scp с вашего компьютера:
# scp -r * user@your-server:/opt/tys/
```

### 2.3 Создание виртуального окружения

```bash
cd /opt/tys
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## ⚙️ Шаг 3: Настройка конфигурации

### 3.1 Создание файла .env

```bash
cd /opt/tys
cp .env.example .env
nano .env
```

Заполните `.env` файл:

```env
SPOTIFY_CLIENT_ID=ваш_spotify_client_id
SPOTIFY_CLIENT_SECRET=ваш_spotify_client_secret
SPOTIFY_REDIRECT_URI=https://tys.flurisrv.ru/callback/spotify
APP_URL=https://tys.flurisrv.ru
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
LOG_LEVEL=INFO
```

**Важно:** Сгенерируйте SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3.2 Проверка конфигурации

```bash
source venv/bin/activate
python -c "from config import settings; settings.validate_required_fields(); print('✅ Конфигурация валидна')"
```

## 🌐 Шаг 4: Настройка Nginx

### 4.1 Создание конфигурации Nginx

```bash
sudo nano /etc/nginx/sites-available/tys
```

Вставьте следующую конфигурацию:

```nginx
server {
    listen 80;
    server_name tys.flurisrv.ru;

    # Логи
    access_log /var/log/nginx/tys_access.log;
    error_log /var/log/nginx/tys_error.log;

    # Максимальный размер загружаемых файлов
    client_max_body_size 10M;

    # Проксирование на FastAPI приложение
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        
        # Заголовки для корректной работы
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Таймауты для долгих операций
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### 4.2 Активация конфигурации

```bash
# Создаем симлинк
sudo ln -s /etc/nginx/sites-available/tys /etc/nginx/sites-enabled/

# Удаляем дефолтную конфигурацию (опционально)
sudo rm -f /etc/nginx/sites-enabled/default

# Проверяем конфигурацию
sudo nginx -t

# Перезагружаем Nginx
sudo systemctl reload nginx
```

## 🔒 Шаг 5: Настройка SSL (Let's Encrypt)

### 5.1 Получение SSL сертификата

```bash
sudo certbot --nginx -d tys.flurisrv.ru
```

Следуйте инструкциям:
- Введите email для уведомлений
- Согласитесь с условиями использования
- Certbot автоматически обновит конфигурацию Nginx

### 5.2 Проверка автопродления

```bash
# Тестовый запуск обновления
sudo certbot renew --dry-run

# Проверка таймера
sudo systemctl status certbot.timer
```

Certbot автоматически продлевает сертификаты через systemd timer.

## 🔄 Шаг 6: Создание systemd service

### 6.1 Создание service файла

```bash
sudo nano /etc/systemd/system/tys.service
```

Вставьте следующее содержимое:

```ini
[Unit]
Description=Yandex Music to Spotify Transfer App
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/tys
Environment="PATH=/opt/tys/venv/bin"
EnvironmentFile=/opt/tys/.env

# Команда запуска
ExecStart=/opt/tys/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log

# Перезапуск при сбое
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=tys

# Ограничения безопасности
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Примечание:** Если вы используете другого пользователя, замените `www-data` на вашего пользователя.

### 6.2 Настройка прав доступа

```bash
# Устанавливаем владельца для директории проекта
sudo chown -R www-data:www-data /opt/tys

# Устанавливаем права на .env (только чтение для владельца)
sudo chmod 600 /opt/tys/.env
```

### 6.3 Активация и запуск service

```bash
# Перезагружаем systemd для загрузки нового сервиса
sudo systemctl daemon-reload

# Включаем автозапуск при загрузке системы
sudo systemctl enable tys

# Запускаем сервис
sudo systemctl start tys

# Проверяем статус
sudo systemctl status tys
```

### 6.4 Просмотр логов

```bash
# Логи приложения
sudo journalctl -u tys -f

# Или последние 100 строк
sudo journalctl -u tys -n 100
```

## ✅ Шаг 7: Проверка работы

### 7.1 Проверка статуса сервисов

```bash
# Проверка приложения
sudo systemctl status tys

# Проверка Nginx
sudo systemctl status nginx

# Проверка портов
sudo netstat -tlnp | grep 8000
```

### 7.2 Тестирование через curl

```bash
# Проверка health endpoint
curl http://127.0.0.1:8000/health

# Проверка через домен
curl https://tys.flurisrv.ru/health
```

### 7.3 Проверка в браузере

Откройте в браузере: `https://tys.flurisrv.ru`

## 🔧 Шаг 8: Настройка Spotify OAuth

### 8.1 Добавление Redirect URI в Spotify Dashboard

1. Перейдите на https://developer.spotify.com/dashboard
2. Выберите ваше приложение
3. Нажмите "Edit Settings"
4. В разделе "Redirect URIs" добавьте:
   ```
   https://tys.flurisrv.ru/callback/spotify
   ```
5. Сохраните изменения

## 📊 Мониторинг и обслуживание

### Просмотр логов

```bash
# Логи приложения (systemd)
sudo journalctl -u tys -f

# Логи Nginx
sudo tail -f /var/log/nginx/tys_access.log
sudo tail -f /var/log/nginx/tys_error.log
```

### Перезапуск сервисов

```bash
# Перезапуск приложения
sudo systemctl restart tys

# Перезапуск Nginx
sudo systemctl restart nginx

# Перезапуск обоих
sudo systemctl restart tys nginx
```

### Обновление приложения

```bash
cd /opt/tys

# Если используете Git
git pull

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем зависимости
pip install -r requirements.txt

# Перезапускаем сервис
sudo systemctl restart tys
```

### Резервное копирование

Рекомендуется регулярно делать резервную копию:
- Файла `.env` (с секретными ключами)
- Кода приложения

```bash
# Пример скрипта резервного копирования
tar -czf /backup/tys-$(date +%Y%m%d).tar.gz /opt/tys
```

## 🐛 Решение проблем

### Приложение не запускается

```bash
# Проверьте логи
sudo journalctl -u tys -n 50

# Проверьте конфигурацию
cd /opt/tys
source venv/bin/activate
python -c "from config import settings; print(settings)"
```

### Ошибки с правами доступа

```bash
# Проверьте владельца файлов
ls -la /opt/tys

# Исправьте права (если нужно)
sudo chown -R www-data:www-data /opt/tys
```

### Nginx возвращает 502 Bad Gateway

```bash
# Проверьте, запущено ли приложение
sudo systemctl status tys

# Проверьте порт
sudo netstat -tlnp | grep 8000

# Проверьте логи Nginx
sudo tail -f /var/log/nginx/tys_error.log
```

### SSL сертификат не обновляется

```bash
# Проверьте статус certbot
sudo systemctl status certbot.timer

# Принудительное обновление
sudo certbot renew
```

## 🔒 Безопасность

### Дополнительные меры безопасности

1. **Ограничение доступа к .env:**
   ```bash
   sudo chmod 600 /opt/tys/.env
   sudo chown root:root /opt/tys/.env  # Если нужно
   ```

2. **Настройка fail2ban (защита от брутфорса):**
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

3. **Регулярные обновления:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## 📝 Итоговая проверка

После выполнения всех шагов проверьте:

- [ ] DNS запись настроена (A-запись для `tys.flurisrv.ru`)
- [ ] Приложение запущено (`sudo systemctl status tys`)
- [ ] Nginx работает (`sudo systemctl status nginx`)
- [ ] SSL сертификат активен (`https://tys.flurisrv.ru`)
- [ ] Приложение доступно через домен
- [ ] Spotify OAuth настроен с правильным Redirect URI
- [ ] Логи не содержат ошибок

---

**Готово!** Ваше приложение должно быть доступно по адресу `https://tys.flurisrv.ru` 🎉

