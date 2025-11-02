# Быстрый старт

## Шаг 1: Создайте файл .env

Создайте файл `.env` в корне проекта и заполните его:

**Для продакшена (tys.flurisrv.ru):**
```env
SPOTIFY_CLIENT_ID=ваш_spotify_client_id
SPOTIFY_CLIENT_SECRET=ваш_spotify_client_secret
SPOTIFY_REDIRECT_URI=https://tys.flurisrv.ru/callback/spotify
APP_URL=https://tys.flurisrv.ru
SECRET_KEY=сгенерируйте_случайный_ключ_64_символа
LOG_LEVEL=INFO
```

**Для генерации SECRET_KEY запустите:**
```bash
python generate_secret_key.py
```

Или вручную:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Для локальной разработки:**
```env
SPOTIFY_CLIENT_ID=ваш_spotify_client_id
SPOTIFY_CLIENT_SECRET=ваш_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8000/callback/spotify
APP_URL=http://localhost:8000
SECRET_KEY=dev_secret_key
LOG_LEVEL=INFO
```

**Важно:** Используйте тот вариант, который соответствует вашему окружению. Для продакшена - `tys.flurisrv.ru`, для тестирования локально - `localhost`.

## Шаг 2: Получите Spotify Client ID и Secret

1. Перейдите на https://developer.spotify.com/dashboard
2. Войдите в аккаунт Spotify
3. Нажмите "Create app"
4. Заполните форму:
   - App name: любое название
   - App description: описание (опционально)
   - Redirect URI: `http://localhost:8000/callback/spotify` (для разработки) или `https://tys.flurisrv.ru/callback/spotify` (для продакшена)
5. Примите условия использования
6. После создания скопируйте:
   - **Client ID** → `SPOTIFY_CLIENT_ID`
   - **Client Secret** → `SPOTIFY_CLIENT_SECRET` (нажмите "View client secret")

## Шаг 3: Запустите приложение

```bash
python main.py
```

Или:

```bash
python run.py
```

Или через uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Готово!

Откройте браузер и перейдите на `http://localhost:8000`

---

**Примечание:** Если вы получили ошибку о том, что переменные окружения не найдены, убедитесь, что:
1. Файл `.env` существует в корне проекта (там же, где `main.py`)
2. Файл `.env` содержит все обязательные переменные
3. Нет лишних пробелов вокруг знака `=` в `.env` файле

