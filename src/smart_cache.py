#!/usr/bin/env python3
"""
Smart Cache - 智慧快取系統

升級版語意快取，支援：
- SQLite 持久化
- TTL 過期機制
- 統計監控
- 相似度匹配

基於 v2.2.1 semantic_cache.py 升級
"""

import hashlib
import sqlite3
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import re


class SmartCache:
    """智慧快取系統
    
    功能：
    - SQLite 持久化
    - TTL 過期機制
    - 相似度匹配
    - 統計監控
    
    Attributes:
        similarity_threshold: 相似度閾值，默認 0.85
        ttl: 過期時間（秒），默認 24 小時
    """
    
    def __init__(
        self,
        db_path: str = "./data/smart_cache.db",
        similarity_threshold: float = 0.85,
        ttl: int = 86400  # 24 小時
    ):
        """初始化智慧快取
        
        Args:
            db_path: SQLite 資料庫路徑
            similarity_threshold: 相似度閾值，範圍 0-1
            ttl: 過期時間（秒），默認 24 小時
        """
        self.db_path = db_path
        self.similarity_threshold = similarity_threshold
        self.ttl = ttl
        
        # 初始化資料庫
        self._init_db()
        
        # 內存緩存（用於快速訪問）
        self._memory_cache: Dict[str, Dict] = {}
    
    def _init_db(self):
        """初始化 SQLite 資料庫"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # 建立表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT UNIQUE NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                hit_count INTEGER DEFAULT 1,
                last_hit_at REAL
            )
        """)
        
        # 建立索引
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompt_hash ON cache(prompt_hash)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
        """)
        
        self.conn.commit()
    
    def _normalize(self, text: str) -> str:
        """標準化文本"""
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _get_key(self, text: str) -> str:
        """生成快取鍵"""
        normalized = self._normalize(text)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """計算相似度 - 優化版 Jaccard + 編輯距離"""
        # Jaccard
        words1 = set(self._normalize(text1).split())
        words2 = set(self._normalize(text2).split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        jaccard = intersection / union if union > 0 else 0.0
        
        # 簡單的長度懲罰
        len_ratio = min(len(text1), len(text2)) / max(len(text1), len(text2))
        
        # 組合分數
        return (jaccard * 0.7) + (len_ratio * 0.3)
    
    def _cleanup_expired(self):
        """清理過期快取"""
        now = time.time()
        cursor = self.conn.execute(
            "DELETE FROM cache WHERE expires_at < ?",
            (now,)
        )
        self.conn.commit()
        
        if cursor.rowcount > 0:
            print(f"🧹 清理了 {cursor.rowcount} 個過期快取")
    
    def get(self, prompt: str) -> Optional[str]:
        """獲取快取結果
        
        Args:
            prompt: 查詢文本
            
        Returns:
            快取的回覆，若無匹配則返回 None
        """
        # 定期清理過期（10% 機率）
        import random
        if random.random() < 0.1:
            self._cleanup_expired()
        
        key = self._get_key(prompt)
        now = time.time()
        
        # 1. 內存緩存（最快）
        if key in self._memory_cache:
            cached = self._memory_cache[key]
            if cached["expires_at"] > now:
                # 更新命中
                self._update_hit(key)
                return cached["response"]
            else:
                del self._memory_cache[key]
        
        # 2. 精確匹配
        cursor = self.conn.execute(
            """SELECT * FROM cache 
               WHERE prompt_hash = ? AND expires_at > ?""",
            (key, now)
        )
        row = cursor.fetchone()
        
        if row:
            # 更新內存緩存
            self._memory_cache[key] = {
                "response": row["response"],
                "expires_at": row["expires_at"]
            }
            # 更新命中
            self._update_hit(key)
            return row["response"]
        
        # 3. 相似匹配
        return self._similar_search(prompt)
    
    def _similar_search(self, prompt: str) -> Optional[str]:
        """相似度搜索"""
        now = time.time()
        
        # 獲取所有未過期的快取
        cursor = self.conn.execute(
            "SELECT prompt, response, expires_at FROM cache WHERE expires_at > ?",
            (now,)
        )
        
        best_match = None
        best_score = 0.0
        
        for row in cursor:
            score = self._calculate_similarity(prompt, row["prompt"])
            
            if score >= self.similarity_threshold and score > best_score:
                best_score = score
                best_match = {
                    "prompt": row["prompt"],
                    "response": row["response"],
                    "expires_at": row["expires_at"],
                    "score": score
                }
        
        if best_match:
            # 存入內存緩存
            key = self._get_key(prompt)
            self._memory_cache[key] = {
                "response": best_match["response"],
                "expires_at": best_match["expires_at"]
            }
            print(f"📍 相似匹配: {best_score:.2%}")
            return best_match["response"]
        
        return None
    
    def _update_hit(self, prompt_hash: str):
        """更新命中計數"""
        now = time.time()
        self.conn.execute(
            """UPDATE cache 
               SET hit_count = hit_count + 1, last_hit_at = ?
               WHERE prompt_hash = ?""",
            (now, prompt_hash)
        )
        self.conn.commit()
    
    def set(self, prompt: str, response: str, ttl: int = None):
        """設置快取
        
        Args:
            prompt: 查詢文本
            response: 回覆文本
            ttl: 過期時間（秒），None 使用默認
        """
        key = self._get_key(prompt)
        now = time.time()
        expires_at = now + (ttl or self.ttl)
        
        # 存入資料庫
        self.conn.execute("""
            INSERT OR REPLACE INTO cache 
            (prompt_hash, prompt, response, created_at, expires_at, hit_count, last_hit_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (key, prompt, response, now, expires_at, now))
        self.conn.commit()
        
        # 存入內存
        self._memory_cache[key] = {
            "response": response,
            "expires_at": expires_at
        }
    
    def clear(self, expired_only: bool = True):
        """清除快取
        
        Args:
            expired_only: 是否只清除過期的
        """
        if expired_only:
            self._cleanup_expired()
        else:
            self.conn.execute("DELETE FROM cache")
            self.conn.commit()
            self._memory_cache.clear()
        
        # VACUUM 優化
        self.conn.execute("VACUUM")
        self.conn.commit()
    
    def stats(self) -> Dict[str, Any]:
        """快取統計
        
        Returns:
            完整的統計信息
        """
        now = time.time()
        
        # 總數
        cursor = self.conn.execute("SELECT COUNT(*) as total FROM cache")
        total = cursor.fetchone()["total"]
        
        # 未過期
        cursor = self.conn.execute(
            "SELECT COUNT(*) as active FROM cache WHERE expires_at > ?",
            (now,)
        )
        active = cursor.fetchone()["active"]
        
        # 總命中
        cursor = self.conn.execute(
            "SELECT SUM(hit_count) as hits FROM cache"
        )
        hits = cursor.fetchone()["hits"] or 0
        
        # 平均命中率
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        # 熱門快取
        cursor = self.conn.execute("""
            SELECT prompt, response, hit_count, created_at 
            FROM cache 
            ORDER BY hit_count DESC 
            LIMIT 5
        """)
        top_cache = [
            {
                "prompt": row["prompt"][:50] + "...",
                "hits": row["hit_count"]
            }
            for row in cursor
        ]
        
        return {
            "total": total,
            "active": active,
            "expired": total - active,
            "total_hits": hits,
            "hit_rate": f"{hit_rate:.1f}%",
            "memory_cache_size": len(self._memory_cache),
            "top_cache": top_cache
        }
    
    def get_by_hash(self, prompt_hash: str) -> Optional[str]:
        """通過哈希獲取"""
        now = time.time()
        cursor = self.conn.execute(
            "SELECT response FROM cache WHERE prompt_hash = ? AND expires_at > ?",
            (prompt_hash, now)
        )
        row = cursor.fetchone()
        return row["response"] if row else None
    
    def delete(self, prompt: str) -> bool:
        """刪除指定快取"""
        key = self._get_key(prompt)
        
        # 從資料庫刪除
        cursor = self.conn.execute(
            "DELETE FROM cache WHERE prompt_hash = ?",
            (key,)
        )
        self.conn.commit()
        
        # 從內存刪除
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        return cursor.rowcount > 0
    
    def close(self):
        """關閉連接"""
        self.conn.close()


# ============== 便捷函數 ==============

# 全局實例
_cache: SmartCache = None


def get_cache(
    db_path: str = "./data/smart_cache.db",
    similarity_threshold: float = 0.85,
    ttl: int = 86400
) -> SmartCache:
    """獲取全局 Smart Cache 實例"""
    global _cache
    if _cache is None:
        _cache = SmartCache(db_path, similarity_threshold, ttl)
    return _cache


# ============== 主程式 ==============

if __name__ == "__main__":
    print("=" * 50)
    print("🧠 Smart Cache Test")
    print("=" * 50)
    
    # 初始化
    cache = SmartCache(
        db_path="./data/test_cache.db",
        similarity_threshold=0.8,
        ttl=3600  # 1 小時
    )
    
    # 測試設置
    print("\n📝 設置測試...")
    cache.set("你好，請介紹自己", "我是一個 AI 助手")
    cache.set("你好，請問你是誰", "我是 AI")
    cache.set("Python 是什麼", "一種程式語言")
    
    # 測試獲取
    print("\n📥 獲取測試...")
    result = cache.get("你好，請介紹自己")
    print(f"   精確匹配: {result}")
    
    result2 = cache.get("你好，請問你是誰")
    print(f"   相似匹配: {result2}")
    
    # 統計
    print("\n📊 統計:")
    stats = cache.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 清理
    cache.clear()
    
    print("\n✅ Smart Cache 測試完成!")
