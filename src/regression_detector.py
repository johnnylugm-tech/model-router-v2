"""
LLM 迴歸檢測器 - Regression Detector
監控輸出品質變化、及時發現模型退化、自動告警
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
import json
import os
import logging
import statistics


@dataclass
class QualityMetric:
    """品質指標"""
    timestamp: str
    model_id: str
    task_type: str
    output_length: int
    latency_ms: int
    success: bool
    # 品質評估指標
    response_quality_score: Optional[float] = None  # 0.0 - 1.0
    error_rate: Optional[float] = None  # 0.0 - 1.0
    retry_rate: Optional[float] = None  # 0.0 - 1.0


@dataclass
class RegressionAlert:
    """迴歸告警"""
    timestamp: str
    model_id: str
    alert_type: str
    severity: str  # info, warning, critical
    message: str
    current_value: float
    baseline_value: float
    change_percent: float


@dataclass
class ModelHealthReport:
    """模型健康報告"""
    model_id: str
    status: str  # healthy, degraded, critical
    avg_latency: float
    avg_quality_score: float
    error_rate: float
    trend: str  # improving, stable, degrading
    last_check: str
    alerts: List[RegressionAlert]


class RegressionDetector:
    """迴歸檢測器"""
    
    def __init__(
        self,
        data_dir: str = None,
        alert_callback: Optional[Callable[[RegressionAlert], None]] = None
    ):
        """
        初始化迴歸檢測器
        
        Args:
            data_dir: 數據存儲目錄
            alert_callback: 告警回調函數
        """
        self.data_dir = data_dir or os.path.expanduser("~/.model-router")
        self.metrics_file = os.path.join(self.data_dir, "quality_metrics.json")
        self.alerts_file = os.path.join(self.data_dir, "regression_alerts.json")
        
        # 內存存儲
        self._metrics: List[QualityMetric] = []
        self._alerts: List[RegressionAlert] = []
        
        # 告警回調
        self._alert_callback = alert_callback
        
        # 配置參數
        self.baseline_window = 100  # 基線窗口大小
        self.degradation_threshold = 0.2  # 退化閾值 (20%)
        self.critical_threshold = 0.4  # 嚴重閾值 (40%)
        self.min_samples = 10  # 最小樣本數
        
        # 緩存
        self._model_baselines: Dict[str, Dict] = {}
        
        # 日誌
        self.logger = logging.getLogger(__name__)
        
        # 加載數據
        self._load_metrics()
        self._load_alerts()
    
    def _load_metrics(self) -> None:
        """加載品質指標"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    self._metrics = [
                        QualityMetric(**m) for m in data.get('metrics', [])
                    ]
            except Exception as e:
                self.logger.warning(f"加載品質指標失敗: {e}")
                self._metrics = []
    
    def _save_metrics(self) -> None:
        """保存品質指標"""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.metrics_file, 'w') as f:
            json.dump({
                'metrics': [
                    {
                        'timestamp': m.timestamp,
                        'model_id': m.model_id,
                        'task_type': m.task_type,
                        'output_length': m.output_length,
                        'latency_ms': m.latency_ms,
                        'success': m.success,
                        'response_quality_score': m.response_quality_score,
                        'error_rate': m.error_rate,
                        'retry_rate': m.retry_rate,
                    }
                    for m in self._metrics
                ]
            }, f, indent=2)
    
    def _load_alerts(self) -> None:
        """加載告警"""
        if os.path.exists(self.alerts_file):
            try:
                with open(self.alerts_file, 'r') as f:
                    data = json.load(f)
                    self._alerts = [
                        RegressionAlert(**a) for a in data.get('alerts', [])
                    ]
            except Exception:
                self._alerts = []
    
    def _save_alerts(self) -> None:
        """保存告警"""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.alerts_file, 'w') as f:
            json.dump({
                'alerts': [
                    {
                        'timestamp': a.timestamp,
                        'model_id': a.model_id,
                        'alert_type': a.alert_type,
                        'severity': a.severity,
                        'message': a.message,
                        'current_value': a.current_value,
                        'baseline_value': a.baseline_value,
                        'change_percent': a.change_percent,
                    }
                    for a in self._alerts
                ]
            }, f, indent=2)
    
    def record_metric(
        self,
        model_id: str,
        task_type: str,
        output_length: int,
        latency_ms: int,
        success: bool,
        response_quality_score: float = None,
        error_rate: float = None,
        retry_rate: float = None
    ) -> None:
        """記錄品質指標"""
        metric = QualityMetric(
            timestamp=datetime.now().isoformat(),
            model_id=model_id,
            task_type=task_type,
            output_length=output_length,
            latency_ms=latency_ms,
            success=success,
            response_quality_score=response_quality_score,
            error_rate=error_rate,
            retry_rate=retry_rate
        )
        
        self._metrics.append(metric)
        self._save_metrics()
        
        # 每次記錄後檢測迴歸
        self._check_regression(model_id)
    
    def _get_model_metrics(
        self, 
        model_id: str, 
        limit: int = None
    ) -> List[QualityMetric]:
        """獲取模型的指標"""
        metrics = [m for m in self._metrics if m.model_id == model_id]
        if limit:
            return metrics[-limit:]
        return metrics
    
    def _calculate_baseline(
        self, 
        model_id: str
    ) -> Dict[str, float]:
        """計算基線"""
        metrics = self._get_model_metrics(model_id, self.baseline_window)
        
        if len(metrics) < self.min_samples:
            return {}
        
        # 只使用歷史數據（前 80%）作為基線
        baseline_count = int(len(metrics) * 0.8)
        baseline_metrics = metrics[:baseline_count]
        
        if not baseline_metrics:
            return {}
        
        return {
            'avg_latency': statistics.mean(m.latency_ms for m in baseline_metrics),
            'avg_output_length': statistics.mean(m.output_length for m in baseline_metrics),
            'success_rate': sum(1 for m in baseline_metrics if m.success) / len(baseline_metrics),
            'sample_size': len(baseline_metrics)
        }
    
    def _check_regression(self, model_id: str) -> None:
        """檢測迴歸"""
        recent_metrics = self._get_model_metrics(model_id, self.baseline_window)
        
        if len(recent_metrics) < self.min_samples:
            return
        
        # 分離基線和當前數據
        baseline_count = int(len(recent_metrics) * 0.8)
        baseline = recent_metrics[:baseline_count]
        current = recent_metrics[baseline_count:]
        
        if not baseline or not current:
            return
        
        # 計算當前指標
        current_latency = statistics.mean(m.latency_ms for m in current)
        current_success_rate = sum(1 for m in current if m.success) / len(current)
        
        # 計算基線指標
        baseline_latency = statistics.mean(m.latency_ms for m in baseline)
        baseline_success_rate = sum(1 for m in baseline if m.success) / len(baseline)
        
        # 檢測延遲退化
        if baseline_latency > 0:
            latency_change = (current_latency - baseline_latency) / baseline_latency
            
            if latency_change > self.critical_threshold:
                self._create_alert(
                    model_id=model_id,
                    alert_type="latency_degradation",
                    severity="critical",
                    message=f"延遲嚴重退化: {current_latency:.0f}ms vs 基線 {baseline_latency:.0f}ms",
                    current_value=current_latency,
                    baseline_value=baseline_latency,
                    change_percent=latency_change * 100
                )
            elif latency_change > self.degradation_threshold:
                self._create_alert(
                    model_id=model_id,
                    alert_type="latency_degradation",
                    severity="warning",
                    message=f"延遲上升: {current_latency:.0f}ms vs 基線 {baseline_latency:.0f}ms",
                    current_value=current_latency,
                    baseline_value=baseline_latency,
                    change_percent=latency_change * 100
                )
        
        # 檢測成功率下降
        if baseline_success_rate > 0:
            success_change = (baseline_success_rate - current_success_rate) / baseline_success_rate
            
            if success_change > self.critical_threshold:
                self._create_alert(
                    model_id=model_id,
                    alert_type="success_rate_degradation",
                    severity="critical",
                    message=f"成功率大幅下降: {current_success_rate:.1%} vs 基線 {baseline_success_rate:.1%}",
                    current_value=current_success_rate,
                    baseline_value=baseline_success_rate,
                    change_percent=success_change * 100
                )
            elif success_change > self.degradation_threshold:
                self._create_alert(
                    model_id=model_id,
                    alert_type="success_rate_degradation",
                    severity="warning",
                    message=f"成功率下降: {current_success_rate:.1%} vs 基線 {baseline_success_rate:.1%}",
                    current_value=current_success_rate,
                    baseline_value=baseline_success_rate,
                    change_percent=success_change * 100
                )
    
    def _create_alert(
        self,
        model_id: str,
        alert_type: str,
        severity: str,
        message: str,
        current_value: float,
        baseline_value: float,
        change_percent: float
    ) -> None:
        """創建告警"""
        alert = RegressionAlert(
            timestamp=datetime.now().isoformat(),
            model_id=model_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            current_value=current_value,
            baseline_value=baseline_value,
            change_percent=change_percent
        )
        
        self._alerts.append(alert)
        self._save_alerts()
        
        # 觸發回調
        if self._alert_callback:
            self._alert_callback(alert)
        
        self.logger.warning(f"🚨 迴歸告警 [{severity}]: {message}")
    
    def get_model_health(
        self, 
        model_id: str
    ) -> ModelHealthReport:
        """獲取模型健康報告"""
        metrics = self._get_model_metrics(model_id)
        
        if not metrics:
            return ModelHealthReport(
                model_id=model_id,
                status="unknown",
                avg_latency=0,
                avg_quality_score=0,
                error_rate=1.0,
                trend="unknown",
                last_check=datetime.now().isoformat(),
                alerts=[]
            )
        
        # 計算當前指標
        recent = metrics[-self.baseline_window:]
        avg_latency = statistics.mean(m.latency_ms for m in recent)
        avg_output_length = statistics.mean(m.output_length for m in recent)
        success_count = sum(1 for m in recent if m.success)
        success_rate = success_count / len(recent)
        
        # 品質分數
        quality_scores = [
            m.response_quality_score 
            for m in recent 
            if m.response_quality_score is not None
        ]
        avg_quality = statistics.mean(quality_scores) if quality_scores else success_rate
        
        # 錯誤率
        error_rate = 1 - success_rate
        
        # 判斷狀態
        if error_rate > 0.5 or avg_quality < 0.5:
            status = "critical"
        elif error_rate > 0.2 or avg_quality < 0.7:
            status = "degraded"
        else:
            status = "healthy"
        
        # 判斷趨勢
        if len(metrics) >= self.baseline_window * 2:
            early = metrics[:self.baseline_window]
            late = metrics[-self.baseline_window:]
            
            early_success = sum(1 for m in early if m.success) / len(early)
            late_success = sum(1 for m in late if m.success) / len(late)
            
            if late_success > early_success * 1.1:
                trend = "improving"
            elif late_success < early_success * 0.9:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # 獲取相關告警
        model_alerts = [
            a for a in self._alerts 
            if a.model_id == model_id
        ][-5:]  # 最近 5 條
        
        return ModelHealthReport(
            model_id=model_id,
            status=status,
            avg_latency=avg_latency,
            avg_quality_score=avg_quality,
            error_rate=error_rate,
            trend=trend,
            last_check=datetime.now().isoformat(),
            alerts=model_alerts
        )
    
    def get_all_models_health(self) -> List[ModelHealthReport]:
        """獲取所有模型健康狀態"""
        model_ids = set(m.model_id for m in self._metrics)
        return [self.get_model_health(mid) for mid in model_ids]
    
    def check_all_models(self) -> str:
        """檢查所有模型並返回報告"""
        reports = self.get_all_models_health()
        
        if not reports:
            return "尚無模型數據"
        
        lines = [
            "=" * 60,
            "🔍 LLM 迴歸檢測報告",
            "=" * 60,
        ]
        
        for report in reports:
            status_emoji = {
                "healthy": "✅",
                "degraded": "⚠️",
                "critical": "❌",
                "unknown": "❓"
            }.get(report.status, "❓")
            
            trend_emoji = {
                "improving": "📈",
                "stable": "➡️",
                "degrading": "📉",
                "unknown": "❓"
            }.get(report.trend, "❓")
            
            lines.extend([
                f"\n{status_emoji} 模型: {report.model_id}",
                f"   狀態: {report.status.upper()} | 趨勢: {trend_emoji} {report.trend}",
                f"   平均延遲: {report.avg_latency:.0f}ms",
                f"   品質分數: {report.avg_quality_score:.1%}",
                f"   錯誤率: {report.error_rate:.1%}",
            ])
            
            if report.alerts:
                lines.append(f"   🚨 最近告警 ({len(report.alerts)}):")
                for alert in report.alerts[-2:]:
                    severity_icon = "🔴" if alert.severity == "critical" else "🟡"
                    lines.append(f"      {severity_icon} [{alert.severity}] {alert.message}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def get_recent_alerts(
        self, 
        hours: int = 24,
        severity: str = None
    ) -> List[RegressionAlert]:
        """獲取最近的告警"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        alerts = [
            a for a in self._alerts
            if datetime.fromisoformat(a.timestamp) >= cutoff
        ]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def clear_metrics(self) -> None:
        """清除指標數據"""
        self._metrics.clear()
        if os.path.exists(self.metrics_file):
            os.remove(self.metrics_file)
    
    def clear_alerts(self) -> None:
        """清除告警"""
        self._alerts.clear()
        if os.path.exists(self.alerts_file):
            os.remove(self.alerts_file)


# 便捷函數
def get_regression_detector() -> RegressionDetector:
    """獲取迴歸檢測器實例"""
    return RegressionDetector()
