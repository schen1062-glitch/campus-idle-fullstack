import asyncio
from typing import Any, Optional
from redis.asyncio import Redis, ConnectionPool

from app.core.config import settings

# 全局 Redis 连接池
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None

async def get_redis() -> Redis:
    """获取 Redis 客户端（懒加载）"""
    global _redis_pool, _redis_client
    
    if _redis_client is None:
        _redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True
        )
        _redis_client = Redis(connection_pool=_redis_pool)
    return _redis_client

async def close_redis():
    """关闭 Redis 连接"""
    global _redis_pool, _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None

class RedisQueue:
    """Redis List 实现的简单可靠队列"""
    
    def __init__(self, queue_name: str = "task_queue"):
        self.queue_name = f"queue:{queue_name}"
    
    async def enqueue(self, item: dict) -> str:
        """入队"""
        redis = await get_redis()
        import json
        await redis.lpush(self.queue_name, json.dumps(item))
        return "ok"
    
    async def dequeue(self, timeout: int = 0) -> Optional[dict]:
        """出队（阻塞）"""
        redis = await get_redis()
        import json
        item = await redis.brpop(self.queue_name, timeout=timeout)
        if item:
            return json.loads(item[1])
        return None
    
    async def ack(self, item: dict):
        """确认处理完成（当前实现中无需额外操作，List 队列出队即消费）"""
        pass
    
    async def requeue(self, item: dict):
        """重新入队"""
        await self.enqueue(item)
    
    async def size(self) -> int:
        """队列当前长度"""
        redis = await get_redis()
        return await redis.llen(self.queue_name)
