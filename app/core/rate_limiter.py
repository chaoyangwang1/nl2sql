"""基于滑动窗口的简单内存限流器"""
import asyncio
import time
from collections import defaultdict


class RateLimiter:
    """滑动窗口限流器，按 key（如 IP）限制每秒请求数"""

    def __init__(self, max_requests: int = 10, window_seconds: float = 1.0):
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        """检查 key 是否允许本次请求，允许则记录并返回 True"""
        now = time.monotonic()
        async with self._lock:
            # 清理过期记录
            window_start = now - self._window
            self._requests[key] = [t for t in self._requests[key] if t > window_start]

            if len(self._requests[key]) >= self._max_requests:
                return False

            self._requests[key].append(now)
            return True

    async def clear(self) -> None:
        async with self._lock:
            self._requests.clear()


# 全局查询限流器：每秒最多 5 次请求
query_rate_limiter = RateLimiter(max_requests=5, window_seconds=1.0)
