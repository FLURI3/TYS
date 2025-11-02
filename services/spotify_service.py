"""
Сервис для работы с Spotify API
"""
import logging
from typing import List, Dict, Optional
import aiohttp
import base64

from config import settings

logger = logging.getLogger(__name__)


class SpotifyService:
    """Класс для взаимодействия с Spotify API"""
    
    BASE_URL = "https://api.spotify.com/v1"
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    
    def __init__(self, access_token: str):
        """
        Инициализация сервиса
        
        Args:
            access_token: OAuth access token Spotify
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Обновляет access_token используя refresh_token
        
        Args:
            refresh_token: Refresh token от Spotify
            
        Returns:
            Новый access_token или None при ошибке
        """
        try:
            auth_string = f"{settings.spotify_client_id}:{settings.spotify_client_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.TOKEN_URL,
                    data=token_data,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to refresh token: {await response.text()}")
                        return None
                    
                    token_response = await response.json()
                    return token_response.get("access_token")
        
        except Exception as e:
            logger.exception(f"Error refreshing token: {e}")
            return None
    
    async def get_current_user(self) -> Dict:
        """
        Получает информацию о текущем пользователе
        
        Returns:
            Словарь с информацией о пользователе
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/me",
                    headers=self.headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to get user info: {error_text}")
                        raise Exception(f"Failed to get user info: {response.status}")
                    
                    return await response.json()
        
        except Exception as e:
            logger.exception(f"Error getting current user: {e}")
            raise
    
    async def search_track(self, title: str, artist: str) -> Optional[Dict]:
        """
        Ищет трек в Spotify по названию и исполнителю
        
        Args:
            title: Название трека
            artist: Исполнитель
            
        Returns:
            Словарь с информацией о найденном треке или None
        """
        try:
            # Формируем поисковый запрос
            # Пытаемся найти точное совпадение или близкое
            query_parts = []
            
            if title:
                # Убираем скобки и дополнительную информацию в названии
                clean_title = title.split("(")[0].split("[")[0].strip()
                query_parts.append(f"track:{clean_title}")
            
            if artist:
                # Берем первого исполнителя (если их несколько через запятую)
                clean_artist = artist.split(",")[0].strip()
                query_parts.append(f"artist:{clean_artist}")
            
            query = " ".join(query_parts) if query_parts else title
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/search",
                    headers=self.headers,
                    params={
                        "q": query,
                        "type": "track",
                        "limit": 5  # Проверяем первые 5 результатов
                    }
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Search failed for '{artist} - {title}': {response.status}")
                        return None
                    
                    search_data = await response.json()
                    tracks = search_data.get("tracks", {}).get("items", [])
                    
                    if not tracks:
                        return None
                    
                    # Пытаемся найти наиболее подходящий трек
                    # Проверяем совпадение названия и исполнителя
                    title_lower = title.lower().split("(")[0].split("[")[0].strip()
                    artist_lower = artist.lower()
                    
                    for track in tracks:
                        track_title = track.get("name", "").lower()
                        track_artists = [a.get("name", "").lower() for a in track.get("artists", [])]
                        
                        # Проверяем совпадение названия
                        title_match = title_lower in track_title or track_title in title_lower
                        
                        # Проверяем совпадение хотя бы одного исполнителя
                        artist_match = any(
                            artist_part in track_artist or track_artist in artist_part
                            for artist_part in artist_lower.split(",")
                            for track_artist in track_artists
                        )
                        
                        if title_match and artist_match:
                            return {
                                "id": track.get("id"),
                                "uri": track.get("uri"),
                                "name": track.get("name"),
                                "artists": [a.get("name") for a in track.get("artists", [])]
                            }
                    
                    # Если точного совпадения нет, возвращаем первый результат
                    logger.debug(f"Exact match not found for '{artist} - {title}', using first result")
                    first_track = tracks[0]
                    return {
                        "id": first_track.get("id"),
                        "uri": first_track.get("uri"),
                        "name": first_track.get("name"),
                        "artists": [a.get("name") for a in first_track.get("artists", [])]
                    }
        
        except Exception as e:
            logger.warning(f"Error searching track '{artist} - {title}': {e}")
            return None
    
    async def create_playlist(self, user_id: str, name: str, description: str = "") -> Dict:
        """
        Создаёт новый плейлист в Spotify
        
        Args:
            user_id: ID пользователя Spotify
            name: Название плейлиста
            description: Описание плейлиста
            
        Returns:
            Словарь с информацией о созданном плейлисте
        """
        try:
            playlist_data = {
                "name": name,
                "description": description or f"Импортировано из Яндекс Музыки",
                "public": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/users/{user_id}/playlists",
                    headers=self.headers,
                    json=playlist_data
                ) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        logger.error(f"Failed to create playlist: {error_text}")
                        raise Exception(f"Failed to create playlist: {response.status}")
                    
                    return await response.json()
        
        except Exception as e:
            logger.exception(f"Error creating playlist: {e}")
            raise
    
    async def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str]) -> bool:
        """
        Добавляет треки в плейлист
        
        Args:
            playlist_id: ID плейлиста
            track_ids: Список ID треков для добавления
            
        Returns:
            True если успешно, False иначе
        """
        try:
            # Формируем список URI треков
            track_uris = [f"spotify:track:{track_id}" for track_id in track_ids]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/playlists/{playlist_id}/tracks",
                    headers=self.headers,
                    json={"uris": track_uris}
                ) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        logger.error(f"Failed to add tracks to playlist: {error_text}")
                        return False
                    
                    return True
        
        except Exception as e:
            logger.exception(f"Error adding tracks to playlist: {e}")
            return False

