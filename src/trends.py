"""
趨勢分析儀表板 - Trends Analyzer
追蹤任務類型分佈、模型使用頻率、成本趨勢
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os


@dataclass
class TrendReport:
    """趨勢報告"""
    period: str
    task_type_distribution: Dict[str, int]
    model_usage_frequency: Dict[str, int]
    cost_trend: List[Dict]
    total_requests: int
    total_cost: float
    avg_latency: float
    top_model: str
    top_task_type: str


class TrendsAnalyzer:
    """趨勢分析器"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化趨勢分析器
        
        Args:
            data_dir: 數據存儲目錄
        """
        self.data_dir = data_dir or os.path.expanduser("~/.model-router")
        self.history_file = os.path.join(self.data_dir, "trends_history.json")
        
        # 內存緩存
        self._requests: List[Dict] = []
        self._load_history()
    
    def _load_history(self) -> None:
        """加載歷史數據"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self._requests = data.get('requests', [])
            except Exception:
                self._requests = []
    
    def _save_history(self) -> None:
        """保存歷史數據"""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.history_file, 'w') as f:
            json.dump({'requests': self._requests}, f)
    
    def record_request(
        self,
        model_id: str,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: int,
        success: bool,
        timestamp: str = None
    ) -> None:
        """記錄請求"""
        record = {
            'timestamp': timestamp or datetime.now().isoformat(),
            'model_id': model_id,
            'task_type': task_type,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost': cost,
            'latency_ms': latency_ms,
            'success': success
        }
        self._requests.append(record)
        self._save_history()
    
    def get_task_type_distribution(
        self, 
        days: int = 7
    ) -> Dict[str, int]:
        """獲取任務類型分佈"""
        cutoff = datetime.now() - timedelta(days=days)
        distribution = defaultdict(int)
        
        for req in self._requests:
            ts = datetime.fromisoformat(req['timestamp'])
            if ts >= cutoff:
                distribution[req['task_type']] += 1
        
        return dict(distribution)
    
    def get_model_usage_frequency(
        self, 
        days: int = 7
    ) -> Dict[str, int]:
        """獲取模型使用頻率"""
        cutoff = datetime.now() - timedelta(days=days)
        frequency = defaultdict(int)
        
        for req in self._requests:
            ts = datetime.fromisoformat(req['timestamp'])
            if ts >= cutoff:
                frequency[req['model_id']] += 1
        
        return dict(frequency)
    
    def get_cost_trend(
        self, 
        days: int = 7,
        granularity: str = "day"
    ) -> List[Dict]:
        """獲取成本趨勢"""
        cutoff = datetime.now() - timedelta(days=days)
        trend = defaultdict(lambda: {'cost': 0.0, 'requests': 0})
        
        for req in self._requests:
            ts = datetime.fromisoformat(req['timestamp'])
            if ts >= cutoff:
                if granularity == "day":
                    key = ts.strftime("%Y-%m-%d")
                elif granularity == "hour":
                    key = ts.strftime("%Y-%m-%d %H:00")
                else:
                    key = ts.strftime("%Y-%m-%d")
                
                trend[key]['cost'] += req['cost']
                trend[key]['requests'] += 1
        
        return [
            {'period': k, 'cost': v['cost'], 'requests': v['requests']}
            for k, v in sorted(trend.items())
        ]
    
    def get_period_summary(self, days: int = 7) -> TrendReport:
        """獲取週期摘要"""
        cutoff = datetime.now() - timedelta(days=days)
        
        period_requests = [
            r for r in self._requests
            if datetime.fromisoformat(r['timestamp']) >= cutoff
        ]
        
        total_requests = len(period_requests)
        
        # 任務類型分佈
        task_dist = defaultdict(int)
        for r in period_requests:
            task_dist[r['task_type']] += 1
        
        # 模型使用頻率
        model_freq = defaultdict(int)
        for r in period_requests:
            model_freq[r['model_id']] += 1
        
        # 成本趨勢
        cost_trend = self.get_cost_trend(days)
        
        # 總成本
        total_cost = sum(r['cost'] for r in period_requests)
        
        # 平均延遲
        latencies = [r['latency_ms'] for r in period_requests]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        # Top 排行
        top_model = max(model_freq.items(), key=lambda x: x[1]) if model_freq else ("N/A", 0)
        top_task = max(task_dist.items(), key=lambda x: x[1]) if task_dist else ("N/A", 0)
        
        return TrendReport(
            period=f"最近 {days} 天",
            task_type_distribution=dict(task_dist),
            model_usage_frequency=dict(model_freq),
            cost_trend=cost_trend,
            total_requests=total_requests,
            total_cost=total_cost,
            avg_latency=avg_latency,
            top_model=top_model[0],
            top_task_type=top_task[0]
        )
    
    def generate_report(self, days: int = 7) -> str:
        """生成趨勢報告"""
        report = self.get_period_summary(days)
        
        lines = [
            "=" * 60,
            "📈 Model Router 趨勢分析報告",
            "=" * 60,
            f"📅 統計週期: {report.period}",
            "-" * 60,
            f"📊 總請求數: {report.total_requests}",
            f"💰 總成本: ${report.total_cost:.4f}",
            f"⏱️  平均延遲: {report.avg_latency:.0f}ms",
            "-" * 60,
            "🏆 Top 排行",
            f"  最常用模型: {report.top_model}",
            f"  最常任務: {report.top_task_type}",
            "-" * 60,
            "📊 任務類型分佈:",
        ]
        
        for task, count in sorted(
            report.task_type_distribution.items(),
            key=lambda x: -x[1]
        ):
            pct = count / report.total_requests * 100 if report.total_requests > 0 else 0
            lines.append(f"  • {task}: {count} ({pct:.1f}%)")
        
        lines.extend([
            "-" * 60,
            "🤖 模型使用頻率:",
        ])
        
        for model, count in sorted(
            report.model_usage_frequency.items(),
            key=lambda x: -x[1]
        ):
            pct = count / report.total_requests * 100 if report.total_requests > 0 else 0
            lines.append(f"  • {model}: {count} ({pct:.1f}%)")
        
        if report.cost_trend:
            lines.extend([
                "-" * 60,
                "💵 成本趨勢:",
            ])
            for trend in report.cost_trend[-7:]:  # 顯示最近7個週期
                lines.append(
                    f"  • {trend['period']}: ${trend['cost']:.4f} ({trend['requests']} 請求)"
                )
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def reset(self) -> None:
        """重置歷史數據"""
        self._requests.clear()
        if os.path.exists(self.history_file):
            os.remove(self.history_file)


# 便捷函數
def get_trends_analyzer() -> TrendsAnalyzer:
    """獲取趨勢分析器實例"""
    return TrendsAnalyzer()
