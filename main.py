"""
Yandex Music → Spotify Transfer Web App
Главный файл FastAPI приложения
"""
import logging
import secrets
import time
from typing import Optional, Dict, List
from urllib.parse import urlencode

import aiohttp
from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from services.yandex_service import YandexMusicService
from services.spotify_service import SpotifyService

# Проверяем обязательные поля конфигурации
try:
    settings.validate_required_fields()
except ValueError as e:
    import sys
    print(f"\n❌ Ошибка конфигурации:\n{e}\n", file=sys.stderr)
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация FastAPI
app = FastAPI(
    title="Yandex Music → Spotify Transfer",
    description="Перенос плейлиста 'Мне нравится' из Яндекс Музыки в Spotify",
    version="1.0.0"
)

# CORS middleware
# В продакшене разрешаем только основной домен, в разработке - localhost
cors_origins = [settings.app_url]
if "localhost" in settings.app_url or "127.0.0.1" in settings.app_url:
    cors_origins.extend(["http://localhost:8000", "http://127.0.0.1:8000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Временное хранилище сессий (в продакшене можно использовать Redis)
# Храним только access_token и refresh_token во время сессии пользователя
session_storage: Dict[str, Dict] = {}


def generate_session_id() -> str:
    """Генерирует уникальный ID сессии"""
    return secrets.token_urlsafe(32)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/auth/spotify")
async def spotify_auth():
    """
    Инициирует OAuth авторизацию Spotify
    Редиректит пользователя на Spotify Authorization URL
    """
    # Параметры для OAuth запроса
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": "playlist-modify-public playlist-modify-private user-read-private",
        "show_dialog": "false"
    }
    
    auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    
    logger.info("Redirecting to Spotify authorization")
    return RedirectResponse(url=auth_url)


@app.get("/callback/spotify")
async def spotify_callback(code: Optional[str] = None, error: Optional[str] = None):
    """
    Callback endpoint для получения authorization code от Spotify
    Обменивает code на access_token и refresh_token
    """
    if error:
        logger.error(f"Spotify OAuth error: {error}")
        return RedirectResponse(url=f"{settings.app_url}/?error=spotify_auth_failed")
    
    if not code:
        logger.error("No authorization code received from Spotify")
        return RedirectResponse(url=f"{settings.app_url}/?error=no_code")
    
    try:
        # Обмен code на токены
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.spotify_redirect_uri,
        }
        
        async with aiohttp.ClientSession() as session:
            # Подготовка Basic Auth
            import base64
            auth_string = f"{settings.spotify_client_id}:{settings.spotify_client_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            async with session.post(
                "https://accounts.spotify.com/api/token",
                data=token_data,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Spotify token exchange failed: {error_text}")
                    return RedirectResponse(url=f"{settings.app_url}/?error=token_exchange_failed")
                
                token_response = await response.json()
                access_token = token_response.get("access_token")
                refresh_token = token_response.get("refresh_token")
                expires_in = token_response.get("expires_in", 3600)
                
                if not access_token:
                    logger.error("No access_token in Spotify response")
                    return RedirectResponse(url=f"{settings.app_url}/?error=no_access_token")
                
                # Генерируем session_id и сохраняем токены
                session_id = generate_session_id()
                session_storage[session_id] = {
                    "spotify_access_token": access_token,
                    "spotify_refresh_token": refresh_token,
                    "expires_at": time.time() + expires_in,
                    "created_at": time.time()
                }
                
                logger.info(f"Spotify authorization successful, session_id: {session_id[:8]}...")
                
                # Редирект на главную с session_id
                return RedirectResponse(url=f"{settings.app_url}/?session_id={session_id}&spotify_auth=success")
    
    except Exception as e:
        logger.exception(f"Error during Spotify callback: {e}")
        return RedirectResponse(url=f"{settings.app_url}/?error=callback_error")


@app.post("/transfer")
async def transfer_playlist(
    yandex_token: str = Form(...),
    session_id: str = Form(...)
):
    """
    Основной endpoint для переноса плейлиста
    Принимает токен Яндекс и session_id для Spotify токенов
    """
    # Проверяем наличие сессии Spotify
    if session_id not in session_storage:
        raise HTTPException(status_code=401, detail="Spotify session not found. Please authorize again.")
    
    session_data = session_storage[session_id]
    spotify_access_token = session_data.get("spotify_access_token")
    
    if not spotify_access_token:
        raise HTTPException(status_code=401, detail="Spotify access token not found")
    
    # Проверяем срок действия токена
    if time.time() > session_data.get("expires_at", 0):
        # Пытаемся обновить токен
        spotify_service = SpotifyService(spotify_access_token)
        new_token = await spotify_service.refresh_access_token(session_data.get("spotify_refresh_token"))
        if new_token:
            session_data["spotify_access_token"] = new_token
            spotify_access_token = new_token
        else:
            raise HTTPException(status_code=401, detail="Spotify token expired. Please authorize again.")
    
    try:
        # Получаем треки из Яндекс Музыки
        logger.info("Fetching tracks from Yandex Music...")
        yandex_service = YandexMusicService(yandex_token)
        yandex_tracks = await yandex_service.get_liked_tracks()
        
        if not yandex_tracks:
            raise HTTPException(status_code=400, detail="No tracks found in Yandex Music 'Мне нравится' playlist")
        
        logger.info(f"Found {len(yandex_tracks)} tracks in Yandex Music")
        
        # Ищем треки в Spotify и создаём плейлист
        spotify_service = SpotifyService(spotify_access_token)
        
        # Получаем информацию о пользователе
        user_info = await spotify_service.get_current_user()
        user_id = user_info.get("id")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Could not get Spotify user ID")
        
        # Создаём плейлист
        playlist_name = "Яндекс Музыка – Мои лайки"
        playlist = await spotify_service.create_playlist(user_id, playlist_name)
        playlist_id = playlist.get("id")
        playlist_url = playlist.get("external_urls", {}).get("spotify")
        
        if not playlist_id:
            raise HTTPException(status_code=500, detail="Failed to create Spotify playlist")
        
        logger.info(f"Created playlist: {playlist_id}")
        
        # Ищем треки в Spotify
        found_tracks = []
        not_found_tracks = []
        
        for track in yandex_tracks:
            spotify_track = await spotify_service.search_track(
                track["title"],
                track["artist"]
            )
            
            if spotify_track:
                found_tracks.append(spotify_track["id"])
                logger.debug(f"Found: {track['artist']} - {track['title']}")
            else:
                not_found_tracks.append({
                    "artist": track["artist"],
                    "title": track["title"]
                })
                logger.debug(f"Not found: {track['artist']} - {track['title']}")
        
        # Добавляем найденные треки в плейлист (по 100 за раз - лимит Spotify API)
        if found_tracks:
            for i in range(0, len(found_tracks), 100):
                batch = found_tracks[i:i + 100]
                await spotify_service.add_tracks_to_playlist(playlist_id, batch)
                logger.info(f"Added {len(batch)} tracks to playlist (batch {i//100 + 1})")
        
        # Очищаем сессию после успешного переноса
        # Можно оставить для возможности повторного использования
        # del session_storage[session_id]
        
        # Возвращаем результат
        return JSONResponse({
            "success": True,
            "playlist_url": playlist_url,
            "playlist_id": playlist_id,
            "total_tracks": len(yandex_tracks),
            "found_tracks": len(found_tracks),
            "not_found_tracks": not_found_tracks
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error during transfer: {e}")
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "Yandex Music → Spotify Transfer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )

