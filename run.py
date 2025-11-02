#!/usr/bin/env python3
"""
Скрипт для запуска приложения
"""
import sys
import uvicorn

# Импортируем main, который проверит конфигурацию
try:
    from main import app
    from config import settings
except ValueError as e:
    print(f"\n❌ Ошибка конфигурации:\n{e}\n", file=sys.stderr)
    print("Создайте файл .env на основе .env.example")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Ошибка при запуске:\n{e}\n", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # В продакшене отключить reload
        log_level=settings.log_level.lower(),
        access_log=True
    )

