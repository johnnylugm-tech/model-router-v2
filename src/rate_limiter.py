#!/usr/bin/env python3
"""
Rate Limiter - 流量控制

功能：
- 請求速率限制
- 配額管理
- 排隊機制
"""

import time
import sqlite3
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from threading import Lock


@dataclass
class RateLimit:
    """速率限制配置"""
    requests_per_minute: int = 60  # 每分鐘請求數
    requests_per_hour: int = 1000   # 每小時請求數
    requests_per_day: int = 10000  # 每天請求數
    burst_size: int = 10           # 突發大小


@dataclass
class Quota:
    """配額配置"""
    daily_limit: int = 10000     # 每日限額
    monthly_limit: int = 100000   # 每月限額


class RateLimiter:
    """速率限制器"""
    
    def __init__(
        self,
        rate_limit: RateLimit = None,
        quota: Quota = None,
        db_path: str = "./data/rate_limit.db"
    ):
        """
        初始化速率限制器
        
        Args:
            rate_limit: 速率限制配置
            quota: 配額配置
            db_path: 資料庫路徑
        """
        self.rate_limit = rate_limit or RateLimit()
        self.quota = quota or Quota()
        self.db_path = db_path
        
        # 初始化資料庫
        self._init_db()
        
        # 內存計數器（用於快速訪問）
        self._minute_requests = deque()  # 每分鐘請求時間戳
        self._hour_requests = deque()    # 每小時請求時間戳
        self._day_requests = deque()     # 每天請求時間戳
        
        self._lock = Lock()
    
    def _init_db(self):
        """初始化資料庫"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 添加這行
        
        # 建立表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                user_id TEXT DEFAULT 'default',
                endpoint TEXT,
                allowed INTEGER
            )
        """)
        
        # 建立索引
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON requests(timestamp)
        """)
        
        self.conn.commit()
    
    def _cleanup_old_requests(self):
        """清理舊請求記錄"""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400
        
        # 從內存清理
        while self._minute_requests and self._minute_requests[0] < minute_ago:
            self._minute_requests.popleft()
        
        while self._hour_requests and self._hour_requests[0] < hour_ago:
            self._hour_requests.popleft()
        
        while self._day_requests and self._day_requests[0] < day_ago:
            self._day_requests.popleft()
        
        # 從資料庫清理（異步）
        self.conn.execute("DELETE FROM requests WHERE timestamp < ?", (day_ago,))
        self.conn.commit()
    
    def check(self, user_id: str = "default") -> Dict[str, Any]:
        """
        檢查是否允許請求
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            包含允許狀態和限制信息的字典
        """
        with self._lock:
            self._cleanup_old_requests()
            
            now = time.time()
            
            # 檢查每分鐘限制
            minute_count = len(self._minute_requests)
            minute_allowed = minute_count < self.rate_limit.requests_per_minute
            
            # 檢查每小時限制
            hour_count = len(self._hour_requests)
            hour_allowed = hour_count < self.rate_limit.requests_per_hour
            
            # 檢查每天限制
            day_count = len(self._day_requests)
            day_allowed = day_count < self.rate_limit.requests_per_day
            
            # 檢查配額
            quota = self._check_quota(user_id)
            
            # 最終決定
            allowed = minute_allowed and hour_allowed and day_allowed and quota["allowed"]
            
            # 記錄請求
            if allowed:
                self._minute_requests.append(now)
                self._hour_requests.append(now)
                self._day_requests.append(now)
                
                self.conn.execute("""
                    INSERT INTO requests (timestamp, user_id, allowed)
                    VALUES (?, ?, ?)
                """, (now, user_id, 1))
                self.conn.commit()
            
            # 計算下次可用時間
            next_available = 0
            if not minute_allowed:
                next_available = max(next_available, self._minute_requests[0] + 60 - now)
            if not hour_allowed:
                next_available = max(next_available, self._hour_requests[0] + 3600 - now)
            if not day_allowed:
                next_available = max(next_available, self._day_requests[0] + 86400 - now)
            
            return {
                "allowed": allowed,
                "reason": self._get_block_reason(minute_allowed, hour_allowed, day_allowed, quota),
                "limits": {
                    "minute": {
                        "current": minute_count,
                        "limit": self.rate_limit.requests_per_minute,
                        "remaining": max(0, self.rate_limit.requests_per_minute - minute_count)
                    },
                    "hour": {
                        "current": hour_count,
                        "limit": self.rate_limit.requests_per_hour,
                        "remaining": max(0, self.rate_limit.requests_per_hour - hour_count)
                    },
                    "day": {
                        "current": day_count,
                        "limit": self.rate_limit.requests_per_day,
                        "remaining": max(0, self.rate_limit.requests_per_day - day_count)
                    }
                },
                "quota": quota,
                "next_available_in": max(0, int(next_available))
            }
    
    def _check_quota(self, user_id: str) -> Dict[str, Any]:
        """檢查配額"""
        today = datetime.now().date().isoformat()
        
        # 獲取今日使用
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        
        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM requests WHERE timestamp > ? AND user_id = ?",
            (start_of_day, user_id)
        )
        daily_used = cursor.fetchone()["count"]
        
        allowed = daily_used < self.quota.daily_limit
        
        return {
            "allowed": allowed,
            "daily_used": daily_used,
            "daily_limit": self.quota.daily_limit,
            "remaining": max(0, self.quota.daily_limit - daily_used)
        }
    
    def _get_block_reason(
        self,
        minute_allowed: bool,
        hour_allowed: bool,
        day_allowed: bool,
        quota: Dict
    ) -> str:
        """獲取阻止原因"""
        if not minute_allowed:
            return "rate_limit_minute"
        if not hour_allowed:
            return "rate_limit_hour"
        if not day_allowed:
            return "rate_limit_day"
        if not quota["allowed"]:
            return "quota_exceeded"
        return "allowed"
    
    def wait_time(self) -> int:
        """計算需要等待的時間（秒）"""
        result = self.check()
        return result.get("next_available_in", 0)
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        return {
            "current": {
                "minute": len(self._minute_requests),
                "hour": len(self._hour_requests),
                "day": len(self._day_requests)
            },
            "limits": {
                "minute": self.rate_limit.requests_per_minute,
                "hour": self.rate_limit.requests_per_hour,
                "day": self.rate_limit.requests_per_day
            },
            "quota": {
                "daily": self.quota.daily_limit,
                "monthly": self.quota.monthly_limit
            }
        }
    
    def reset(self, user_id: str = None):
        """重置計數器"""
        with self._lock:
            if user_id:
                # 只重置特定用戶
                start_of_day = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
                self.conn.execute(
                    "DELETE FROM requests WHERE timestamp > ? AND user_id = ?",
                    (start_of_day, user_id)
                )
            else:
                # 重置所有
                self.conn.execute("DELETE FROM requests")
            
            self.conn.commit()
            
            # 清空內存
            self._minute_requests.clear()
            self._hour_requests.clear()
            self._day_requests.clear()
    
    def close(self):
        """關閉連接"""
        self.conn.close()


# ============== 使用示例 ==============

if __name__ == "__main__":
    print("=" * 50)
    print("⏱️ Rate Limiter Test")
    print("=" * 50)
    
    # 創建限制器
    limiter = RateLimiter(
        rate_limit=RateLimit(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000
        ),
        quota=Quota(daily_limit=500)
    )
    
    # 測試請求
    print("\n📝 測試請求...")
    for i in range(15):
        result = limiter.check(f"user_{i % 3}")
        status = "✅" if result["allowed"] else "❌"
        print(f"   {status} 請求 {i+1}: {result['reason']}")
    
    # 統計
    print("\n📊 統計:")
    stats = limiter.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 等待時間
    wait = limiter.wait_time()
    print(f"\n⏳ 需要等待: {wait}秒")
    
    limiter.close()
    print("\n✅ 測試完成!")
