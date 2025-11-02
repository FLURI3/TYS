"""
Конфигурация приложения
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Spotify OAuth
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "https://tys.flurisrv.ru/callback/spotify"
    
    # Application
    app_url: str = "https://tys.flurisrv.ru"
    secret_key: str = "change-this-secret-key-in-production"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def validate_required_fields(self):
        """Проверяет наличие обязательных полей"""
        if not self.spotify_client_id or not self.spotify_client_secret:
            raise ValueError(
                "Требуются переменные окружения SPOTIFY_CLIENT_ID и SPOTIFY_CLIENT_SECRET.\n"
                "Создайте файл .env на основе .env.example и заполните необходимые поля.\n"
                "См. README.md для инструкций."
            )


# Глобальный экземпляр настроек
try:
    settings = Settings()
    # Проверяем обязательные поля только при реальном использовании
    # (не при импорте, чтобы можно было показать понятную ошибку)
except Exception as e:
    print(f"Ошибка загрузки конфигурации: {e}")
    print("\nСоздайте файл .env со следующими переменными:")
    print("SPOTIFY_CLIENT_ID=ваш_client_id")
    print("SPOTIFY_CLIENT_SECRET=ваш_client_secret")
    print("SPOTIFY_REDIRECT_URI=https://tys.flurisrv.ru/callback/spotify  (или http://localhost:8000/callback/spotify для разработки)")
    print("APP_URL=https://tys.flurisrv.ru  (или http://localhost:8000 для разработки)")
    raise

