#!/usr/bin/env python3
"""
Connection Pool - HTTP 連接池

功能：
- HTTP 連接複用
- 連接管理
- 超時控制
"""

import time
import threading
from typing import Dict, Any, Optional, Callable
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from dataclasses import dataclass, field


@dataclass
class Connection:
    """連接"""
    id: str
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    is_valid: bool = True


class ConnectionPool:
    """HTTP 連接池"""
    
    def __init__(
        self,
        max_connections: int = 10,
        max_idle_time: int = 300,  # 5 分鐘
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        初始化連接池
        
        Args:
            max_connections: 最大連接數
            max_idle_time: 最大空閒時間（秒）
            timeout: 請求超時（秒）
            max_retries: 最大重試次數
        """
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 連接會話
        self.session = requests.Session()
        
        # 連接池
        self._pool: Queue = Queue(maxsize=max_connections)
        self._active = 0
        self._lock = threading.Lock()
        
        # 統計
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        發送 GET 請求
        
        Args:
            url: 請求 URL
            **kwargs: 其他參數
            
        Returns:
            響應字典
        """
        return self._request("GET", url, **kwargs)
    
    def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """發送 POST 請求"""
        return self._request("POST", url, **kwargs)
    
    def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """發送請求"""
        self._stats["total_requests"] += 1
        
        # 合併超時設置
        kwargs.setdefault("timeout", self.timeout)
        
        # 添加重試邏輯
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                start_time = time.time()
                
                if method == "GET":
                    response = self.session.get(url, **kwargs)
                elif method == "POST":
                    response = self.session.post(url, **kwargs)
                elif method == "PUT":
                    response = self.session.put(url, **kwargs)
                elif method == "DELETE":
                    response = self.session.delete(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                latency = (time.time() - start_time) * 1000
                
                # 記錄統計
                self._stats["successful_requests"] += 1
                self._stats["total_latency"] += latency
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    "latency_ms": latency,
                    "headers": dict(response.headers)
                }
                
            except requests.exceptions.Timeout as e:
                last_error = f"Timeout: {e}"
                retries += 1
                
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                retries += 1
                
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {e}"
                retries += 1
        
        # 失敗
        self._stats["failed_requests"] += 1
        
        return {
            "success": False,
            "error": last_error,
            "retries": retries
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        avg_latency = (
            self._stats["total_latency"] / self._stats["successful_requests"]
            if self._stats["successful_requests"] > 0 else 0
        )
        
        success_rate = (
            self._stats["successful_requests"] / self._stats["total_requests"] * 100
            if self._stats["total_requests"] > 0 else 0
        )
        
        return {
            "total_requests": self._stats["total_requests"],
            "successful": self._stats["successful_requests"],
            "failed": self._stats["failed_requests"],
            "success_rate": f"{success_rate:.1f}%",
            "avg_latency_ms": f"{avg_latency:.1f}",
            "pool_size": self._pool.qsize(),
            "max_connections": self.max_connections
        }
    
    def close(self):
        """關閉連接池"""
        self.session.close()
    
    def reset_stats(self):
        """重置統計"""
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }


# ============== 使用示例 ==============

if __name__ == "__main__":
    print("=" * 50)
    print("🔗 Connection Pool Test")
    print("=" * 50)
    
    # 創建連接池
    pool = ConnectionPool(
        max_connections=5,
        timeout=10,
        max_retries=2
    )
    
    # 測試請求（使用 httpbin 測試）
    print("\n📝 測試請求...")
    
    # 測試成功請求
    result = pool.get("https://httpbin.org/get")
    print(f"   GET: {'✅' if result['success'] else '❌'} {result.get('status_code', 'error')}")
    
    # 測試 POST
    result = pool.post("https://httpbin.org/post", json={"test": "data"})
    print(f"   POST: {'✅' if result['success'] else '❌'} {result.get('status_code', 'error')}")
    
    # 統計
    print("\n📊 統計:")
    stats = pool.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    pool.close()
    print("\n✅ 測試完成!")
