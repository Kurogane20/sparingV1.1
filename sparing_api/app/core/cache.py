"""
Simple in-memory cache with TTL support.
For production, consider using Redis instead.
"""
import time
from typing import Any, Optional, Dict
from functools import wraps
import asyncio


class TTLCache:
    """Thread-safe in-memory cache with TTL expiration."""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expire_time)
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self._cache:
                value, expire_time = self._cache[key]
                if time.time() < expire_time:
                    return value
                else:
                    # Expired, remove it
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        """Set value in cache with TTL."""
        async with self._lock:
            expire_time = time.time() + ttl_seconds
            self._cache[key] = (value, expire_time)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        async with self._lock:
            self._cache.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, expire_time) in self._cache.items()
                if now >= expire_time
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


# Global cache instance
cache = TTLCache()


# Cache TTL constants (in seconds)
CACHE_TTL_SITES = 300  # 5 minutes
CACHE_TTL_LAST_DATA = 30  # 30 seconds
CACHE_TTL_METRICS = 60  # 1 minute
CACHE_TTL_DEVICES = 120  # 2 minutes


def cache_key(*args) -> str:
    """Generate cache key from arguments."""
    return ":".join(str(arg) for arg in args)


def cached(prefix: str, ttl_seconds: int = 60):
    """
    Decorator for caching async function results.
    
    Usage:
        @cached("sites", ttl_seconds=300)
        async def get_sites():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from prefix and arguments
            key_parts = [prefix]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = cache_key(*key_parts)
            
            # Try to get from cache
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator


async def invalidate_cache(prefix: str) -> None:
    """Invalidate all cache entries with given prefix."""
    async with cache._lock:
        keys_to_delete = [
            key for key in cache._cache.keys()
            if key.startswith(prefix)
        ]
        for key in keys_to_delete:
            del cache._cache[key]
