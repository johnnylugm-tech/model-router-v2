#!/usr/bin/env python3
"""
Cost Budget Alert - 成本預警系統

功能：
- 每日/每週預算上限
- 超過閾值自動通知
- 自動降級到低價模型
"""

import time
import sqlite3
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class AlertLevel(Enum):
    """預警級別"""
    NORMAL = "normal"
    WARNING = "warning"  # 80% 閾值
    CRITICAL = "critical"  # 100% 閾值
    EXCEEDED = "exceeded"  # 超過預算


@dataclass
class Budget:
    """預算配置"""
    daily_limit: float  # 每日預算（美元）
    weekly_limit: float  # 每週預算
    monthly_limit: float  # 每月預算
    warning_threshold: float = 0.8  # 警告閾值（80%）
    critical_threshold: float = 1.0  # 嚴重閾值（100%）
    

@dataclass
class CostRecord:
    """成本記錄"""
    id: Optional[int] = None
    timestamp: str = None
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    user_id: str = "default"
    session_id: str = None


class CostBudgetAlert:
    """成本預警系統"""
    
    def __init__(
        self,
        budget: Budget,
        db_path: str = "./data/cost_budget.db",
        notification_callback: Callable[[AlertLevel, str, float], None] = None
    ):
        """
        初始化成本預警系統
        
        Args:
            budget: 預算配置
            db_path: 資料庫路徑
            notification_callback: 通知回調函數
        """
        self.budget = budget
        self.db_path = db_path
        self.notification_callback = notification_callback
        
        # 初始化資料庫
        self._init_db()
        
        # 緩存當前使用
        self._current_usage = {
            "daily": 0.0,
            "weekly": 0.0,
            "monthly": 0.0
        }
        
        # 更新緩存
        self._update_usage_cache()
    
    def _init_db(self):
        """初始化資料庫"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # 建立表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0,
                user_id TEXT DEFAULT 'default',
                session_id TEXT
            )
        """)
        
        # 建立索引
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON costs(timestamp)
        """)
        
        self.conn.commit()
    
    def _update_usage_cache(self):
        """更新使用量緩存"""
        now = time.time()
        day_ago = now - 86400
        week_ago = now - 604800
        month_ago = now - 2592000
        
        # 每日
        cursor = self.conn.execute(
            "SELECT SUM(cost) as total FROM costs WHERE timestamp > ?",
            (day_ago,)
        )
        self._current_usage["daily"] = cursor.fetchone()["total"] or 0.0
        
        # 每週
        cursor = self.conn.execute(
            "SELECT SUM(cost) as total FROM costs WHERE timestamp > ?",
            (week_ago,)
        )
        self._current_usage["weekly"] = cursor.fetchone()["total"] or 0.0
        
        # 每月
        cursor = self.conn.execute(
            "SELECT SUM(cost) as total FROM costs WHERE timestamp > ?",
            (month_ago,)
        )
        self._current_usage["monthly"] = cursor.fetchone()["total"] or 0.0
    
    def record_cost(self, record: CostRecord) -> Dict[str, Any]:
        """
        記錄成本並檢查預算
        
        Args:
            record: 成本記錄
            
        Returns:
            包含成本和預警信息的字典
        """
        # 設置時間
        if record.timestamp is None:
            record.timestamp = time.time()
        
        # 寫入資料庫
        cursor = self.conn.execute("""
            INSERT INTO costs (timestamp, model, input_tokens, output_tokens, cost, user_id, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.timestamp,
            record.model,
            record.input_tokens,
            record.output_tokens,
            record.cost,
            record.user_id,
            record.session_id
        ))
        self.conn.commit()
        
        # 更新緩存
        self._current_usage["daily"] += record.cost
        self._current_usage["weekly"] += record.cost
        self._current_usage["monthly"] += record.cost
        
        # 檢查預算
        alert = self._check_budget()
        
        return {
            "cost_recorded": record.cost,
            "current_daily": self._current_usage["daily"],
            "daily_limit": self.budget.daily_limit,
            "alert": alert
        }
    
    def _check_budget(self) -> Dict[str, Any]:
        """檢查預算並觸發預警"""
        daily_usage = self._current_usage["daily"]
        daily_limit = self.budget.daily_limit
        
        # 計算使用率
        usage_rate = daily_usage / daily_limit if daily_limit > 0 else 0
        
        # 確定級別
        if usage_rate >= self.budget.critical_threshold:
            level = AlertLevel.EXCEEDED
            message = f"⚠️ 每日預算已超支！ ${daily_usage:.2f} / ${daily_limit:.2f}"
        elif usage_rate >= self.budget.warning_threshold:
            level = AlertLevel.WARNING
            message = f"⚡ 每日預算警告：${daily_usage:.2f} / ${daily_limit:.2f} ({usage_rate:.0%})"
        else:
            level = AlertLevel.NORMAL
            message = f"✅ 正常：${daily_usage:.2f} / ${daily_limit:.2f} ({usage_rate:.0%})"
        
        # 觸發回調
        if self.notification_callback and level != AlertLevel.NORMAL:
            self.notification_callback(level, message, daily_usage)
        
        return {
            "level": level.value,
            "message": message,
            "usage_rate": usage_rate,
            "suggestion": self._get_suggestion(level)
        }
    
    def _get_suggestion(self, level: AlertLevel) -> str:
        """獲取優化建議"""
        if level == AlertLevel.EXCEEDED:
            return "立即停止使用或聯繫管理員增加預算"
        elif level == AlertLevel.WARNING:
            return "建議切換到低價模型（gpt-4o-mini 或 gemini-1.5-flash）"
        else:
            return "使用正常"
    
    def get_current_usage(self) -> Dict[str, float]:
        """獲取當前使用量"""
        self._update_usage_cache()
        return {
            "daily": self._current_usage["daily"],
            "weekly": self._current_usage["weekly"],
            "monthly": self._current_usage["monthly"],
            "daily_limit": self.budget.daily_limit,
            "weekly_limit": self.budget.weekly_limit,
            "monthly_limit": self.budget.monthly_limit
        }
    
    def get_usage_rate(self) -> Dict[str, float]:
        """獲取使用率"""
        usage = self.get_current_usage()
        return {
            "daily_rate": usage["daily"] / usage["daily_limit"] if usage["daily_limit"] > 0 else 0,
            "weekly_rate": usage["weekly"] / usage["weekly_limit"] if usage["weekly_limit"] > 0 else 0,
            "monthly_rate": usage["monthly"] / usage["monthly_limit"] if usage["monthly_limit"] > 0 else 0
        }
    
    def should_use_cheap_model(self) -> bool:
        """是否應該使用低價模型"""
        self._update_usage_cache()
        return self._current_usage["daily"] >= self.budget.daily_limit * self.budget.warning_threshold
    
    def get_cheap_model(self) -> str:
        """獲取推薦的低價模型"""
        return "gpt-4o-mini"  # 或其他低價模型
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        usage = self.get_current_usage()
        rates = self.get_usage_rate()
        
        # 按模型統計
        cursor = self.conn.execute("""
            SELECT model, SUM(cost) as total_cost, COUNT(*) as requests
            FROM costs
            WHERE timestamp > ?
            GROUP BY model
            ORDER BY total_cost DESC
        """, (time.time() - 86400,))
        
        by_model = []
        for row in cursor:
            by_model.append({
                "model": row["model"],
                "cost": row["total_cost"],
                "requests": row["requests"]
            })
        
        return {
            "usage": usage,
            "rates": rates,
            "by_model": by_model,
            "budget": {
                "daily": self.budget.daily_limit,
                "weekly": self.budget.weekly_limit,
                "monthly": self.budget.monthly_limit
            }
        }
    
    def close(self):
        """關閉連接"""
        self.conn.close()


# ============== 使用示例 ==============

if __name__ == "__main__":
    print("=" * 50)
    print("💰 Cost Budget Alert Test")
    print("=" * 50)
    
    # 通知回調
    def notify(level, message, usage):
        print(f"\n🔔 通知: {message}")
    
    # 創建預警系統
    budget = Budget(
        daily_limit=10.0,
        weekly_limit=50.0,
        monthly_limit=200.0,
        warning_threshold=0.8,
        critical_threshold=1.0
    )
    
    alert = CostBudgetAlert(
        budget=budget,
        db_path="./data/test_budget.db",
        notification_callback=notify
    )
    
    # 記錄一些成本
    print("\n📝 記錄成本...")
    
    # 模擬記錄
    for i in range(5):
        record = CostRecord(
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost=0.02,
            user_id="test_user"
        )
        result = alert.record_cost(record)
        print(f"   記錄 {i+1}: {result['alert']['message']}")
    
    # 當前使用
    print("\n📊 當前使用:")
    usage = alert.get_current_usage()
    for key, value in usage.items():
        print(f"   {key}: ${value:.2f}")
    
    # 使用率
    print("\n📈 使用率:")
    rates = alert.get_usage_rate()
    for key, value in rates.items():
        print(f"   {key}: {value:.1%}")
    
    # 統計
    print("\n📋 統計:")
    stats = alert.get_stats()
    print(f"   按模型:")
    for m in stats["by_model"]:
        print(f"      {m['model']}: ${m['cost']:.2f} ({m['requests']} 次)")
    
    # 建議
    print(f"\n💡 建議: {alert.should_use_cheap_model()}")
    if alert.should_use_cheap_model():
        print(f"   推薦模型: {alert.get_cheap_model()}")
    
    alert.close()
    print("\n✅ 測試完成!")
