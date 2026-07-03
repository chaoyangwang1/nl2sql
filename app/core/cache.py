"""基于时间过期的内存缓存，用于缓存查询结果"""
import asyncio
import hashlib
import time


class TTLCache:
    """简单的 TTL 内存缓存，支持异步获取和设置"""

    def __init__(self, ttl_seconds: int = 60, max_size: int = 500):
        self._cache: dict[str, tuple[float, any]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = asyncio.Lock()

    @staticmethod
    def _make_key(query: str) -> str:
        return hashlib.sha256(query.encode("utf-8")).hexdigest()

    async def get(self, query: str) -> any | None:
        key = self._make_key(query)
        async with self._lock:
            if key in self._cache:
                expire_at, value = self._cache[key]
                if time.monotonic() < expire_at:
                    return value
                del self._cache[key]
        return None

    async def set(self, query: str, value: any) -> None:
        key = self._make_key(query)
        async with self._lock:
            # 超过容量时清除最旧的 20%
            if len(self._cache) >= self._max_size:
                expire_count = max(1, int(self._max_size * 0.2))
                sorted_items = sorted(self._cache.items(), key=lambda x: x[1][0])
                for old_key, _ in sorted_items[:expire_count]:
                    del self._cache[old_key]
            self._cache[key] = (time.monotonic() + self._ttl, value)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


# 全局查询缓存实例（60 秒 TTL）
query_cache = TTLCache(ttl_seconds=60)
