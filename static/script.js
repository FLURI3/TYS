// Глобальные переменные
let sessionId = null;
let spotifyAuthorized = false;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем параметры URL
    const urlParams = new URLSearchParams(window.location.search);
    
    // Проверяем наличие session_id от Spotify callback
    const sessionIdParam = urlParams.get('session_id');
    if (sessionIdParam) {
        sessionId = sessionIdParam;
        spotifyAuthorized = true;
        showSpotifyStatus(true);
        showMessage('Авторизация в Spotify успешна!', 'success');
    }
    
    // Проверяем наличие ошибок
    const error = urlParams.get('error');
    if (error) {
        showMessage(getErrorMessage(error), 'error');
    }
    
    // Очищаем URL от параметров
    if (sessionIdParam || error) {
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});

/**
 * Авторизация через Spotify
 */
function authorizeSpotify() {
    window.location.href = '/auth/spotify';
}

/**
 * Показывает статус авторизации Spotify
 */
function showSpotifyStatus(success) {
    const statusEl = document.getElementById('spotify-status');
    statusEl.classList.remove('hidden');
    
    if (success) {
        statusEl.textContent = '✅ Авторизован в Spotify';
        statusEl.className = 'status success';
    } else {
        statusEl.textContent = '❌ Ошибка авторизации';
        statusEl.className = 'status error';
    }
}

/**
 * Показывает сообщение пользователю
 */
function showMessage(text, type = 'info') {
    const messageEl = document.getElementById('message');
    messageEl.textContent = text;
    messageEl.className = `message ${type}`;
    messageEl.classList.remove('hidden');
    
    // Автоматически скрываем через 5 секунд для info и success
    if (type !== 'error') {
        setTimeout(() => {
            messageEl.classList.add('hidden');
        }, 5000);
    }
}

/**
 * Возвращает текст ошибки по коду
 */
function getErrorMessage(errorCode) {
    const errors = {
        'spotify_auth_failed': 'Ошибка авторизации в Spotify. Попробуйте снова.',
        'no_code': 'Не получен код авторизации от Spotify.',
        'token_exchange_failed': 'Ошибка обмена токенов Spotify.',
        'no_access_token': 'Не получен access token от Spotify.',
        'callback_error': 'Ошибка при обработке callback от Spotify.'
    };
    
    return errors[errorCode] || 'Произошла неизвестная ошибка.';
}

/**
 * Перенос плейлиста
 */
async function transferPlaylist() {
    // Проверяем авторизацию Spotify
    if (!spotifyAuthorized || !sessionId) {
        showMessage('Сначала необходимо авторизоваться в Spotify', 'error');
        return;
    }
    
    // Получаем токен Яндекс
    const yandexToken = document.getElementById('yandex-token').value.trim();
    if (!yandexToken) {
        showMessage('Пожалуйста, вставьте токен Яндекс Музыки', 'error');
        document.getElementById('yandex-token').focus();
        return;
    }
    
    // Отключаем кнопку
    const transferBtn = document.getElementById('transfer-btn');
    transferBtn.disabled = true;
    transferBtn.textContent = 'Обработка...';
    
    // Показываем прогресс
    const progressContainer = document.getElementById('progress-container');
    progressContainer.classList.remove('hidden');
    updateProgress(0, 'Начинаем перенос плейлиста...');
    
    // Скрываем результаты если были показаны ранее
    document.getElementById('results').classList.add('hidden');
    
    try {
        // Отправляем запрос на перенос
        const formData = new FormData();
        formData.append('yandex_token', yandexToken);
        formData.append('session_id', sessionId);
        
        updateProgress(10, 'Получение треков из Яндекс Музыки...');
        
        const response = await fetch('/transfer', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Неизвестная ошибка' }));
            throw new Error(errorData.detail || `Ошибка ${response.status}`);
        }
        
        updateProgress(50, 'Поиск треков в Spotify...');
        
        const result = await response.json();
        
        updateProgress(90, 'Добавление треков в плейлист...');
        
        // Показываем результаты
        showResults(result);
        
        updateProgress(100, 'Готово!');
        
        showMessage('Плейлист успешно перенесён!', 'success');
        
    } catch (error) {
        console.error('Transfer error:', error);
        showMessage(`Ошибка при переносе: ${error.message}`, 'error');
        updateProgress(0, 'Произошла ошибка');
    } finally {
        // Включаем кнопку обратно
        transferBtn.disabled = false;
        transferBtn.textContent = 'Перенести плейлист';
        
        // Скрываем прогресс через 2 секунды
        setTimeout(() => {
            progressContainer.classList.add('hidden');
        }, 2000);
    }
}

/**
 * Обновляет прогресс-бар
 */
function updateProgress(percent, text) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressFill.style.width = `${percent}%`;
    progressText.textContent = text;
}

/**
 * Показывает результаты переноса
 */
function showResults(result) {
    const resultsEl = document.getElementById('results');
    resultsEl.classList.remove('hidden');
    
    // Ссылка на плейлист
    const playlistLink = document.getElementById('playlist-link');
    playlistLink.href = result.playlist_url;
    playlistLink.textContent = result.playlist_url;
    
    // Статистика
    document.getElementById('total-tracks').textContent = result.total_tracks;
    document.getElementById('found-tracks').textContent = result.found_tracks;
    document.getElementById('not-found-count').textContent = result.not_found_tracks.length;
    
    // Не найденные треки
    const notFoundContainer = document.getElementById('not-found-tracks');
    const notFoundList = document.getElementById('not-found-list');
    
    if (result.not_found_tracks && result.not_found_tracks.length > 0) {
        notFoundContainer.classList.remove('hidden');
        notFoundList.innerHTML = '';
        
        result.not_found_tracks.forEach(track => {
            const li = document.createElement('li');
            li.textContent = `${track.artist} - ${track.title}`;
            notFoundList.appendChild(li);
        });
    } else {
        notFoundContainer.classList.add('hidden');
    }
    
    // Прокручиваем к результатам
    resultsEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

