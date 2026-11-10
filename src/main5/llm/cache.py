# llm/cache.py
"""响应缓存模块 - 支持会话隔离"""

import hashlib
import threading
import time
from typing import Optional
from config import Config


class ResponseCache:
    """响应缓存 - 支持按会话隔离"""

    def __init__(self, max_size: int = Config.CACHE_MAX_SIZE, ttl: int = Config.CACHE_TTL):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self._lock = threading.Lock()

    def _get_key(self, text: str, intent: str, session_id: str = None) -> str:
        """生成缓存键 - 加入会话ID"""
        normalized = text.lower().strip()[:200]
        if session_id:
            key_base = f"{normalized}_{intent}_{session_id}"
        else:
            key_base = f"{normalized}_{intent}"
        return hashlib.md5(key_base.encode()).hexdigest()

    def get(self, text: str, intent: str, session_id: str = None) -> Optional[str]:
        """获取缓存"""
        with self._lock:
            key = self._get_key(text, intent, session_id)
            if key in self.cache:
                entry = self.cache[key]
                if time.time() - entry['timestamp'] < self.ttl:
                    print(f"💾 缓存命中: session={session_id}")
                    return entry['response']
                else:
                    del self.cache[key]
            return None

    def set(self, text: str, intent: str, response: str, session_id: str = None):
        """设置缓存"""
        with self._lock:
            key = self._get_key(text, intent, session_id)

            if len(self.cache) >= self.max_size:
                oldest = min(self.cache.items(), key=lambda x: x[1]['timestamp'])
                del self.cache[oldest[0]]

            self.cache[key] = {
                'response': response,
                'timestamp': time.time()
            }
            print(f"💾 缓存写入: session={session_id}, key={key[:8]}...")

    def clear_session_cache(self, session_id: str):
        """清除指定会话的所有缓存"""
        with self._lock:
            keys_to_delete = []
            for key, entry in self.cache.items():
                if session_id in key:
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del self.cache[key]
            print(f"🗑️ 清除会话 {session_id} 的缓存: {len(keys_to_delete)} 条")

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self.cache.clear()
            print("🗑️ 所有缓存已清空")

    def get_stats(self) -> dict:
        """获取缓存统计"""
        with self._lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl
            }