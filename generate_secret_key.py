#!/usr/bin/env python3
"""
Скрипт для генерации SECRET_KEY
"""
import secrets

if __name__ == "__main__":
    secret_key = secrets.token_urlsafe(64)
    print("\n" + "="*70)
    print("Сгенерированный SECRET_KEY:")
    print("="*70)
    print(f"SECRET_KEY={secret_key}")
    print("="*70)
    print("\nСкопируйте эту строку в ваш файл .env")
    print("⚠️  Не делитесь этим ключом ни с кем и не коммитьте его в Git!\n")

