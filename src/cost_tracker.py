"""
成本追蹤器 - Cost Tracker
追蹤 API 使用量和成本
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json


@dataclass
class RequestRecord:
    """請求記錄"""
    timestamp: str
    model_id: str
    task_type: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: int
    success: bool
    error: Optional[str] = None


@dataclass
class SessionStats:
    """會話統計"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: int = 0
    model_usage: Dict[str, int] = field(default_factory=dict)


class CostTracker:
    """成本追蹤器"""
    
    def __init__(self):
        self._records: List[RequestRecord] = []
        self._session_stats = SessionStats()
    
    def record_request(
        self,
        model_id: str,
        task_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        latency_ms: int = 0,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """記錄一次請求"""
        record = RequestRecord(
            timestamp=datetime.now().isoformat(),
            model_id=model_id,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            success=success,
            error=error
        )
        
        self._records.append(record)
        self._update_stats(record)
    
    def _update_stats(self, record: RequestRecord) -> None:
        """更新統計"""
        self._session_stats.total_requests += 1
        
        if record.success:
            self._session_stats.successful_requests += 1
        else:
            self._session_stats.failed_requests += 1
        
        self._session_stats.total_input_tokens += record.input_tokens
        self._session_stats.total_output_tokens += record.output_tokens
        self._session_stats.total_cost += record.cost
        self._session_stats.total_latency_ms += record.latency_ms
        
        # 更新模型使用
        model_id = record.model_id
        self._session_stats.model_usage[model_id] = \
            self._session_stats.model_usage.get(model_id, 0) + 1
    
    def get_session_stats(self) -> SessionStats:
        """獲取會話統計"""
        return self._session_stats
    
    def get_summary(self) -> str:
        """獲取摘要"""
        stats = self._session_stats
        
        if stats.total_requests == 0:
            return "尚無請求記錄"
        
        avg_latency = (
            stats.total_latency_ms / stats.total_requests 
            if stats.total_requests > 0 else 0
        )
        success_rate = (
            stats.successful_requests / stats.total_requests * 100
            if stats.total_requests > 0 else 0
        )
        
        lines = [
            "=" * 40,
            "📊 成本追蹤摘要",
            "=" * 40,
            f"總請求數: {stats.total_requests}",
            f"成功: {stats.successful_requests} | 失敗: {stats.failed_requests}",
            f"成功率: {success_rate:.1f}%",
            "-" * 40,
            f"輸入 Tokens: {stats.total_input_tokens:,}",
            f"輸出 Tokens: {stats.total_output_tokens:,}",
            f"總成本: ${stats.total_cost:.4f}",
            f"平均延遲: {avg_latency:.0f}ms",
            "-" * 40,
            "模型使用情況:",
        ]
        
        for model_id, count in sorted(
            stats.model_usage.items(), 
            key=lambda x: -x[1]
        ):
            percentage = count / stats.total_requests * 100
            lines.append(f"  {model_id}: {count} ({percentage:.1f}%)")
        
        lines.append("=" * 40)
        
        return "\n".join(lines)
    
    def get_model_breakdown(self) -> Dict[str, Dict]:
        """獲取模型細分"""
        breakdown: Dict[str, Dict] = {}
        
        for record in self._records:
            if record.model_id not in breakdown:
                breakdown[record.model_id] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "latency_ms": 0,
                    "success_rate": 0.0,
                }
            
            stats = breakdown[record.model_id]
            stats["requests"] += 1
            stats["input_tokens"] += record.input_tokens
            stats["output_tokens"] += record.output_tokens
            stats["cost"] += record.cost
            stats["latency_ms"] += record.latency_ms
        
        # 計算成功率
        for model_id in breakdown:
            model_records = [
                r for r in self._records if r.model_id == model_id
            ]
            success_count = sum(1 for r in model_records if r.success)
            total_count = len(model_records)
            breakdown[model_id]["success_rate"] = (
                success_count / total_count * 100 if total_count > 0 else 0
            )
        
        return breakdown
    
    def export_json(self) -> str:
        """導出為 JSON"""
        return json.dumps({
            "session_stats": {
                "total_requests": self._session_stats.total_requests,
                "successful_requests": self._session_stats.successful_requests,
                "failed_requests": self._session_stats.failed_requests,
                "total_input_tokens": self._session_stats.total_input_tokens,
                "total_output_tokens": self._session_stats.total_output_tokens,
                "total_cost": self._session_stats.total_cost,
                "total_latency_ms": self._session_stats.total_latency_ms,
                "model_usage": self._session_stats.model_usage,
            },
            "records": [
                {
                    "timestamp": r.timestamp,
                    "model_id": r.model_id,
                    "task_type": r.task_type,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost": r.cost,
                    "latency_ms": r.latency_ms,
                    "success": r.success,
                    "error": r.error,
                }
                for r in self._records
            ]
        }, indent=2)
    
    def reset(self) -> None:
        """重置追蹤數據"""
        self._records.clear()
        self._session_stats = SessionStats()
