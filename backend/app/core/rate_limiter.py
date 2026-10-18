""" 滑动窗口限流 """
import time
from functools import lru_cache
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import RateLimitedError
from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)

# 限流窗口固定60秒, 可以配合形成每分钟几次
_WINDOW_SECONDS = 60

class RateLimiter:
    def __init__(self) -> None:
        self._redis = get_redis()

    async def check(self, identity: str) -> None:
        """ 检查命中阈值时，抛限流错误 """
        now = time.time()
        key = f"rag:rate_limit:{identity}"
        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.zremrangebyscore(key, 0, now - _WINDOW_SECONDS)  # ① 清掉窗口外的旧卡片
            await pipe.zcard(key)  # ② 获取窗口内的卡片数
            await pipe.zadd(key, {str(uuid4()): now})  # ③ 添加新卡片
            await pipe.expire(key, _WINDOW_SECONDS)  # ④ 设置过期时间
            _, count, *_ = await pipe.execute()
        limit = settings.rate_limit_per_minute
        if int(count) >= limit:
            logger.warning(
                "达到限流速率: identity=%s count=%s limit=%s",
                identity, count, limit
            )
            raise RateLimitedError(
                f"请求过于频繁，每分钟最多{limit}次，请稍后再试"
            )


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    return RateLimiter()