"""Redis 连接管理"""
import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis 连接池（延迟初始化）
_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """获取 Redis 连接"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


async def publish(channel: str, data: dict) -> None:
    """发布消息到 Redis 频道"""
    try:
        r = await get_redis()
        await r.publish(channel, json.dumps(data, default=str))
    except Exception as e:
        logger.error(f"Redis publish failed: {e}")


async def subscribe(channel: str):
    """订阅 Redis 频道"""
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    return pubsub
