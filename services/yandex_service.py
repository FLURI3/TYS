"""
Сервис для работы с Yandex Music API
"""
import logging
from typing import List, Dict, Optional
import aiohttp

logger = logging.getLogger(__name__)


class YandexMusicService:
    """Класс для взаимодействия с Yandex Music API"""
    
    BASE_URL = "https://api.music.yandex.net"
    
    def __init__(self, token: str):
        """
        Инициализация сервиса
        
        Args:
            token: OAuth токен Яндекс Музыки
        """
        self.token = token
        self.headers = {
            "Authorization": f"OAuth {token}",
            "Content-Type": "application/json"
        }
    
    async def get_liked_tracks(self) -> List[Dict[str, str]]:
        """
        Получает все треки из плейлиста 'Мне нравится'
        
        Returns:
            Список словарей с информацией о треках:
            [
                {
                    "title": "Название трека",
                    "artist": "Исполнитель",
                    "album": "Альбом" (опционально)
                },
                ...
            ]
        """
        tracks = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Получаем информацию о пользователе
                async with session.get(
                    f"{self.BASE_URL}/account/status",
                    headers=self.headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Yandex account status failed: {error_text}")
                        raise Exception(f"Failed to get account status: {response.status}")
                    
                    account_data = await response.json()
                    user_id = account_data.get("result", {}).get("account", {}).get("uid")
                    
                    if not user_id:
                        raise Exception("Could not get user ID from Yandex Music")
                
                # Получаем плейлист "Мне нравится"
                # Используем endpoint для получения лайкнутых треков
                async with session.get(
                    f"{self.BASE_URL}/users/{user_id}/likes/tracks",
                    headers=self.headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Yandex likes tracks failed: {error_text}")
                        raise Exception(f"Failed to get liked tracks: {response.status}")
                    
                    likes_data = await response.json()
                    
                    # Пытаемся получить треки из разных возможных структур ответа
                    result = likes_data.get("result", {})
                    liked_tracks = (
                        result.get("library", {}).get("tracks", []) or
                        result.get("tracks", []) or
                        []
                    )
                    
                    logger.info(f"Found {len(liked_tracks)} liked tracks")
                
                if not liked_tracks:
                    logger.warning("No liked tracks found in Yandex Music")
                    return []
                
                # Получаем детальную информацию о каждом треке
                # Yandex API возвращает ID треков, нужно получить полную информацию
                track_ids = []
                for track in liked_tracks:
                    track_id = track.get("id") or track.get("trackId")
                    if track_id:
                        track_ids.append(track_id)
                
                if not track_ids:
                    logger.warning("No track IDs found")
                    return []
                
                # Получаем информацию о треках батчами (лимит Yandex API - обычно 100)
                batch_size = 100
                for i in range(0, len(track_ids), batch_size):
                    batch_ids = track_ids[i:i + batch_size]
                    
                    try:
                        # Формируем запрос для получения информации о треках
                        async with session.post(
                            f"{self.BASE_URL}/tracks",
                            headers=self.headers,
                            json={"track-ids": batch_ids}
                        ) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                logger.warning(f"Failed to get track details for batch {i//batch_size + 1}: {error_text}")
                                continue
                            
                            tracks_data = await response.json()
                            tracks_list = tracks_data.get("result", [])
                            
                            if not tracks_list:
                                logger.warning(f"No tracks in response for batch {i//batch_size + 1}")
                                continue
                            
                            for track_info in tracks_list:
                                if not track_info:
                                    continue
                                    
                                title = track_info.get("title", "")
                                artists = track_info.get("artists", [])
                                artist_names = [artist.get("name", "") for artist in artists if artist]
                                artist = ", ".join(artist_names) if artist_names else "Unknown Artist"
                                
                                albums = track_info.get("albums", [])
                                album = albums[0].get("title", "") if albums and albums[0] else ""
                                
                                tracks.append({
                                    "title": title,
                                    "artist": artist,
                                    "album": album
                                })
                    
                    except Exception as e:
                        logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                        continue
                
                logger.info(f"Processed {len(tracks)} tracks from Yandex Music")
                return tracks
        
        except Exception as e:
            logger.exception(f"Error getting liked tracks from Yandex: {e}")
            raise
    
    async def validate_token(self) -> bool:
        """
        Проверяет валидность токена Яндекс Музыки
        
        Returns:
            True если токен валидный, False иначе
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/account/status",
                    headers=self.headers
                ) as response:
                    return response.status == 200
        except Exception:
            return False

