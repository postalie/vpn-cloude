"""
Rate Limiter для защиты API от брутфорса и DDoS атак
"""
import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """
    Ограничитель запросов с использованием алгоритма Token Bucket
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Инициализация ограничителя
        
        Args:
            max_requests: Максимальное количество запросов в окно времени
            window_seconds: Размер окна времени в секундах
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = defaultdict(list)
        self._lock = Lock()
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Проверка, разрешён ли запрос для данного идентификатора
        
        Args:
            identifier: Уникальный идентификатор (IP, user_id, etc.)
            
        Returns:
            True если запрос разрешён, False если превышен лимит
        """
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            
            # Очищаем старые запросы за пределами окна
            self._requests[identifier] = [
                ts for ts in self._requests[identifier]
                if ts > window_start
            ]
            
            # Проверяем лимит
            if len(self._requests[identifier]) >= self.max_requests:
                return False
            
            # Добавляем новый запрос
            self._requests[identifier].append(now)
            return True
    
    def get_remaining(self, identifier: str) -> int:
        """
        Получить оставшееся количество запросов
        
        Args:
            identifier: Уникальный идентификатор
            
        Returns:
            Количество оставшихся запросов
        """
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            
            self._requests[identifier] = [
                ts for ts in self._requests[identifier]
                if ts > window_start
            ]
            
            return max(0, self.max_requests - len(self._requests[identifier]))
    
    def reset(self, identifier: str):
        """
        Сбросить счётчик для идентификатора
        
        Args:
            identifier: Уникальный идентификатор
        """
        with self._lock:
            self._requests[identifier] = []


# Глобальные экземпляры для разных эндпоинтов
# Строгий лимит для аутентификации
auth_limiter = RateLimiter(max_requests=5, window_seconds=60)

# Лимит для API запросов (устройства, профиль)
api_limiter = RateLimiter(max_requests=30, window_seconds=60)

# Лимит для подписок (sub_handler)
sub_limiter = RateLimiter(max_requests=100, window_seconds=60)

# Лимит для админских операций
admin_limiter = RateLimiter(max_requests=20, window_seconds=60)


def get_client_identifier(request) -> str:
    """
    Получает уникальный идентификатор клиента для rate limiting
    
    Приоритеты:
    1. X-Forwarded-For (если за proxy)
    2. X-Real-IP
    3. remote (IP из запроса)
    """
    # Проверяем заголовки от proxy
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        # Берём первый IP из цепочки
        return forwarded.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    
    # Fallback на remote
    return request.remote or "unknown"
