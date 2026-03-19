#!/usr/bin/env python3
"""
Audit Logger - 審計日誌

功能：
- 請求審計記錄
- 合規日誌
- 日誌查詢
"""

import time
import sqlite3
import json
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class AuditLevel(Enum):
    """審計級別"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditAction(Enum):
    """審計操作"""
    REQUEST = "request"
    RESPONSE = "response"
    MODEL_SWITCH = "model_switch"
    COST_ALERT = "cost_alert"
    RATE_LIMIT = "rate_limit"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    FAILOVER = "failover"
    AUTH = "auth"
    CONFIG_CHANGE = "config_change"


@dataclass
class AuditLog:
    """審計日誌"""
    id: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    level: str = "info"
    action: str = ""
    user_id: str = "system"
    session_id: str = None
    model: str = None
    details: Dict = field(default_factory=dict)
    success: bool = True
    duration_ms: int = 0
    cost: float = 0.0
    ip_address: str = None
    user_agent: str = None


class AuditLogger:
    """審計日誌系統"""
    
    def __init__(
        self,
        db_path: str = "./data/audit.db",
        retention_days: int = 90,
        on_critical: callable = None
    ):
        """
        初始化審計日誌系統
        
        Args:
            db_path: 資料庫路徑
            retention_days: 保留天數
            on_critical: critical 級別回調
        """
        self.db_path = db_path
        self.retention_days = retention_days
        self.on_critical = on_critical
        
        # 初始化資料庫
        self._init_db()
        
        # 鎖
        self._lock = threading.Lock()
        
        # 緩衝（批量寫入）
        self._buffer: List[AuditLog] = []
        self._buffer_size = 100
    
    def _init_db(self):
        """初始化資料庫"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # 建立表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                level TEXT NOT NULL,
                action TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                model TEXT,
                details TEXT,
                success INTEGER,
                duration_ms INTEGER,
                cost REAL,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        
        # 建立索引
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_logs(timestamp)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_level ON audit_logs(level)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_action ON audit_logs(action)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user ON audit_logs(user_id)
        """)
        
        self.conn.commit()
    
    def log(
        self,
        action: str,
        level: str = "info",
        user_id: str = "system",
        session_id: str = None,
        model: str = None,
        details: Dict = None,
        success: bool = True,
        duration_ms: int = 0,
        cost: float = 0.0,
        ip_address: str = None,
        user_agent: str = None
    ):
        """
        記錄審計日誌
        
        Args:
            action: 操作類型
            level: 級別
            user_id: 用戶 ID
            session_id: 會話 ID
            model: 模型
            details: 詳細信息
            success: 是否成功
            duration_ms: 耗時（毫秒）
            cost: 成本
            ip_address: IP 地址
            user_agent: 用戶代理
        """
        audit = AuditLog(
            timestamp=time.time(),
            level=level,
            action=action,
            user_id=user_id,
            session_id=session_id,
            model=model,
            details=details or {},
            success=success,
            duration_ms=duration_ms,
            cost=cost,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 寫入緩衝
        with self._lock:
            self._buffer.append(audit)
            
            # 如果緩衝滿，寫入資料庫
            if len(self._buffer) >= self._buffer_size:
                self._flush()
        
        # 觸發 critical 回調
        if level == "critical" and self.on_critical:
            self.on_critical(audit)
    
    def _flush(self):
        """刷新緩衝"""
        if not self._buffer:
            return
        
        for audit in self._buffer:
            self.conn.execute("""
                INSERT INTO audit_logs (
                    timestamp, level, action, user_id, session_id, model,
                    details, success, duration_ms, cost, ip_address, user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit.timestamp,
                audit.level,
                audit.action,
                audit.user_id,
                audit.session_id,
                audit.model,
                json.dumps(audit.details),
                1 if audit.success else 0,
                audit.duration_ms,
                audit.cost,
                audit.ip_address,
                audit.user_agent
            ))
        
        self.conn.commit()
        self._buffer.clear()
    
    def query(
        self,
        start_time: float = None,
        end_time: float = None,
        level: str = None,
        action: str = None,
        user_id: str = None,
        session_id: str = None,
        model: str = None,
        success: bool = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        查詢審計日誌
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            level: 級別
            action: 操作
            user_id: 用戶 ID
            session_id: 會話 ID
            model: 模型
            success: 是否成功
            limit: 限制數
            offset: 偏移量
            
        Returns:
            日誌列表
        """
        # 刷新緩衝
        self._flush()
        
        sql = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        
        if start_time:
            sql += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            sql += " AND timestamp <= ?"
            params.append(end_time)
        
        if level:
            sql += " AND level = ?"
            params.append(level)
        
        if action:
            sql += " AND action = ?"
            params.append(action)
        
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        
        if model:
            sql += " AND model = ?"
            params.append(model)
        
        if success is not None:
            sql += " AND success = ?"
            params.append(1 if success else 0)
        
        sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.conn.execute(sql, params)
        
        results = []
        for row in cursor:
            results.append({
                "id": row["id"],
                "timestamp": datetime.fromtimestamp(row["timestamp"]).isoformat(),
                "level": row["level"],
                "action": row["action"],
                "user_id": row["user_id"],
                "session_id": row["session_id"],
                "model": row["model"],
                "details": json.loads(row["details"]) if row["details"] else {},
                "success": bool(row["success"]),
                "duration_ms": row["duration_ms"],
                "cost": row["cost"]
            })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        # 刷新緩衝
        self._flush()
        
        now = time.time()
        day_ago = now - 86400
        week_ago = now - 604800
        
        # 按級別統計
        cursor = self.conn.execute("""
            SELECT level, COUNT(*) as count 
            FROM audit_logs 
            WHERE timestamp > ?
            GROUP BY level
        """, (day_ago,))
        
        by_level = {row["level"]: row["count"] for row in cursor}
        
        # 按操作統計
        cursor = self.conn.execute("""
            SELECT action, COUNT(*) as count 
            FROM audit_logs 
            WHERE timestamp > ?
            GROUP BY action
            ORDER BY count DESC
            LIMIT 10
        """, (day_ago,))
        
        by_action = [{"action": row["action"], "count": row["count"]} for row in cursor]
        
        # 總數
        cursor = self.conn.execute(
            "SELECT COUNT(*) as total FROM audit_logs WHERE timestamp > ?",
            (day_ago,)
        )
        total = cursor.fetchone()["total"]
        
        # 成功率
        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM audit_logs WHERE timestamp > ? AND success = 1",
            (day_ago,)
        )
        success_count = cursor.fetchone()["count"]
        
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "by_level": by_level,
            "by_action": by_action,
            "success_rate": f"{success_rate:.1f}%"
        }
    
    def cleanup(self):
        """清理過期日誌"""
        cutoff = time.time() - (self.retention_days * 86400)
        
        cursor = self.conn.execute(
            "DELETE FROM audit_logs WHERE timestamp < ?",
            (cutoff,)
        )
        self.conn.commit()
        
        # VACUUM
        self.conn.execute("VACUUM")
        self.conn.commit()
    
    def close(self):
        """關閉"""
        self._flush()
        self.conn.close()


# ============== 使用示例 ==============

if __name__ == "__main__":
    print("=" * 50)
    print("📋 Audit Logger Test")
    print("=" * 50)
    
    # 創建審計日誌系統
    logger = AuditLogger(
        db_path="./data/test_audit.db",
        retention_days=30
    )
    
    # 記錄日誌
    print("\n📝 記錄日誌...")
    
    logger.log(
        action="request",
        level="info",
        user_id="user_001",
        model="gpt-4o",
        details={"prompt_tokens": 1000, "completion_tokens": 500},
        success=True,
        duration_ms=1500,
        cost=0.03
    )
    
    logger.log(
        action="model_switch",
        level="info",
        user_id="user_001",
        model="gpt-4o-mini",
        details={"reason": "fallback"}
    )
    
    logger.log(
        action="rate_limit",
        level="warning",
        user_id="user_002",
        details={"limit": 60, "current": 61}
    )
    
    logger.log(
        action="failover",
        level="critical",
        user_id="system",
        details={"error": "API timeout", "fallback_to": "gemini"}
    )
    
    # 查詢
    print("\n📥 查詢日誌...")
    logs = logger.query(limit=5)
    for log in logs:
        print(f"   [{log['level']}] {log['action']}: {log['user_id']}")
    
    # 統計
    print("\n📊 統計:")
    stats = logger.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    logger.close()
    print("\n✅ 測試完成!")
