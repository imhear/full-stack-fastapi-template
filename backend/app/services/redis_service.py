"""
Redis服务层（异步版本）
backend/app/services/redis_service.py
结合两个方案的优点
"""
import json
import pickle
from typing import Any, Optional, Dict, List, Set, Union
from datetime import datetime
from zoneinfo import ZoneInfo
import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings, DEFAULT_TZ


class RedisService:
    """
    Redis服务层（异步）：封装所有Redis操作
    统一处理序列化、错误处理、键前缀管理
    """

    def __init__(self, redis_client: redis.Redis):
        """
        初始化Redis服务

        Args:
            redis_client: Redis客户端实例（异步）
        """
        self.redis = redis_client
        self.key_prefix = settings.REDIS_KEY_PREFIX

    def _make_key(self, key: str) -> str:
        """添加统一前缀的键名"""
        return f"{self.key_prefix}{key}"

    def _serialize(self, value: Any) -> str:
        """序列化值（支持JSON和pickle）"""
        if isinstance(value, (str, int, float, bool, type(None))):
            return json.dumps(value)
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            return pickle.dumps(value).hex()

    def _deserialize(self, value: str, use_pickle: bool = False) -> Any:
        """反序列化值"""
        if not value:
            return None

        if use_pickle:
            try:
                return pickle.loads(bytes.fromhex(value))
            except Exception:
                return value

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    # ==================== 基础操作 ====================

    async def set(self, key: str, value: Any,
                  expire_seconds: Optional[int] = None,
                  use_pickle: bool = False) -> bool:
        """设置键值（支持过期时间）"""
        try:
            full_key = self._make_key(key)
            serialized_value = (pickle.dumps(value).hex() if use_pickle
                                else self._serialize(value))

            if expire_seconds:
                return bool(await self.redis.setex(full_key, expire_seconds, serialized_value))
            else:
                return bool(await self.redis.set(full_key, serialized_value))
        except RedisError as e:
            print(f"Redis set error for key {key}: {e}")
            return False

    async def setex(self, key: str, expire_seconds: int, value: Any) -> bool:
        """设置键值并指定过期时间（简写）"""
        return await self.set(key, value, expire_seconds)

    async def get(self, key: str, use_pickle: bool = False) -> Any:
        """获取键值"""
        try:
            full_key = self._make_key(key)
            value = await self.redis.get(full_key)
            if value is None:
                return None
            return self._deserialize(value, use_pickle)
        except RedisError as e:
            print(f"Redis get error for key {key}: {e}")
            return None

    async def delete(self, *keys: str) -> int:
        """删除一个或多个键"""
        try:
            full_keys = [self._make_key(key) for key in keys]
            return await self.redis.delete(*full_keys)
        except RedisError as e:
            print(f"Redis delete error for keys {keys}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(await self.redis.exists(self._make_key(key)))
        except RedisError as e:
            print(f"Redis exists error for key {key}: {e}")
            return False

    async def expire(self, key: str, expire_seconds: int) -> bool:
        """设置键过期时间"""
        try:
            return bool(await self.redis.expire(self._make_key(key), expire_seconds))
        except RedisError as e:
            print(f"Redis expire error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """获取键剩余生存时间"""
        try:
            return await self.redis.ttl(self._make_key(key))
        except RedisError as e:
            print(f"Redis ttl error for key {key}: {e}")
            return -2  # 表示键不存在

    async def incr(self, key: str) -> int:
        """自增键值"""
        try:
            return await self.redis.incr(self._make_key(key))
        except RedisError as e:
            print(f"Redis incr error for key {key}: {e}")
            return 0

    # ==================== 哈希操作 ====================

    async def hset(self, key: str, field: str, value: Any,
                   use_pickle: bool = False) -> bool:
        """设置哈希字段"""
        try:
            full_key = self._make_key(key)
            serialized_value = (pickle.dumps(value).hex() if use_pickle
                                else self._serialize(value))
            return bool(await self.redis.hset(full_key, field, serialized_value))
        except RedisError as e:
            print(f"Redis hset error for key {key}.{field}: {e}")
            return False

    async def hget(self, key: str, field: str, use_pickle: bool = False) -> Any:
        """获取哈希字段"""
        try:
            full_key = self._make_key(key)
            value = await self.redis.hget(full_key, field)
            if value is None:
                return None
            return self._deserialize(value, use_pickle)
        except RedisError as e:
            print(f"Redis hget error for key {key}.{field}: {e}")
            return None

    async def hgetall(self, key: str, use_pickle: bool = False) -> Dict[str, Any]:
        """获取所有哈希字段"""
        try:
            full_key = self._make_key(key)
            data = await self.redis.hgetall(full_key)
            return {k: self._deserialize(v, use_pickle) for k, v in data.items()}
        except RedisError as e:
            print(f"Redis hgetall error for key {key}: {e}")
            return {}

    # ==================== 业务相关方法 ====================

    async def cache_captcha(self, captcha_id: str, captcha_code: str, expire_seconds: int = 300) -> bool:
        """缓存验证码（复用你现有方案）"""
        key = f"captcha:{captcha_id}"
        return await self.setex(key, expire_seconds, captcha_code)

    async def get_captcha(self, captcha_id: str) -> Optional[str]:
        """获取验证码"""
        key = f"captcha:{captcha_id}"
        return await self.get(key)

    async def record_login_failure(self, username: str) -> int:
        """记录登录失败次数（复用你现有方案）"""
        key = f"login_failures:{username}"
        failures = await self.incr(key)
        if failures == 1:
            await self.expire(key, 3600)  # 1小时过期
        return failures

    async def reset_login_failure(self, username: str) -> bool:
        """重置登录失败次数"""
        key = f"login_failures:{username}"
        lock_key = f"account_lock:{username}"
        await self.delete(key, lock_key)
        return True

    async def lock_account(self, username: str, expire_seconds: int = 1800) -> bool:
        """锁定账号"""
        key = f"account_lock:{username}"
        return await self.setex(key, expire_seconds, "locked")

    async def is_account_locked(self, username: str) -> bool:
        """检查账号是否被锁定"""
        key = f"account_lock:{username}"
        return await self.exists(key)

    async def cache_refresh_token(self, user_id: str, refresh_token: str, expire_seconds: int = 7 * 24 * 3600) -> bool:
        """缓存刷新令牌（复用你现有方案）"""
        key = f"refresh_token:{user_id}"
        return await self.setex(key, expire_seconds, refresh_token)

    async def get_refresh_token(self, user_id: str) -> Optional[str]:
        """获取刷新令牌"""
        key = f"refresh_token:{user_id}"
        return await self.get(key)

    async def delete_refresh_token(self, user_id: str) -> bool:
        """删除刷新令牌"""
        key = f"refresh_token:{user_id}"
        return bool(await self.delete(key))

    # ==================== 健康检查 ====================

    async def ping(self) -> bool:
        """检查Redis连接是否正常"""
        try:
            return bool(await self.redis.ping())
        except RedisError:
            return False

    async def get_info(self) -> Dict[str, Any]:
        """获取Redis服务器信息"""
        try:
            info = await self.redis.info()
            return {
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "db_size": info.get("db0", {}).get("keys", 0),
                "uptime_days": info.get("uptime_in_days")
            }
        except RedisError as e:
            return {"error": str(e)}

    # ==================== 连接管理 ====================

    async def close(self):
        """关闭Redis连接"""
        await self.redis.close()