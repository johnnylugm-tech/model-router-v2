#!/usr/bin/env python3
"""
Prometheus Exporter - 簡化版

功能：
- HTTP 指標導出
- 自定義指標
- /metrics 端點

Note: 需要 prometheus-client 庫
pip install prometheus-client
"""

import time
import threading
from typing import Dict, Any, List
from dataclasses import dataclass, field
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


@dataclass
class Metric:
    """指標"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # counter, gauge, histogram


class SimplePrometheusExporter:
    """簡化版 Prometheus 導出器"""
    
    def __init__(self, port: int = 9090):
        """
        初始化導出器
        
        Args:
            port: HTTP 端口
        """
        self.port = port
        self._metrics: List[Metric] = []
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        
        # HTTP 服務器
        self._server = None
        self._thread = None
    
    def inc_counter(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """增加計數器"""
        key = self._make_key(name, labels)
        self._counters[key] += value
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """設置儀表"""
        key = self._make_key(name, labels)
        self._gauges[key] = value
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """生成鍵"""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        return f"{name}{{{label_str}}}"
    
    def get_metrics(self) -> str:
        """獲取所有指標（Prometheus 格式）"""
        lines = []
        
        # 計數器
        for key, value in self._counters.items():
            lines.append(f"{key}_total {value}")
        
        # 儀表
        for key, value in self._gauges.items():
            lines.append(f"{key} {value}")
        
        return "\n".join(lines) + "\n"
    
    # 便捷方法
    def record_request(self, model: str, success: bool, duration_ms: float):
        """記錄請求"""
        self.inc_counter("model_router_requests_total", 1, {
            "model": model,
            "success": "true" if success else "false"
        })
        self.set_gauge("model_router_request_duration_ms", duration_ms, {"model": model})
    
    def record_cost(self, model: str, cost: float):
        """記錄成本"""
        self.inc_counter("model_router_cost_total", cost, {"model": model})
    
    def record_cache_hit(self, hit: bool):
        """記錄緩存命中"""
        self.inc_counter("model_router_cache_total", 1, {"hit": "true" if hit else "false"})
    
    def record_failover(self, from_model: str, to_model: str):
        """記錄故障轉移"""
        self.inc_counter("model_router_failover_total", 1, {
            "from": from_model,
            "to": to_model
        })
    
    # HTTP 服務器
    def start_server(self):
        """啟動 HTTP 服務器"""
        if self._server:
            return
        
        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/metrics" or self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.end_headers()
                    self.wfile.write(exporter.get_metrics().encode())
                elif self.path == "/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"OK")
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass
        
        self._server = HTTPServer(("0.0.0.0", self.port), MetricsHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        print(f"🚀 Prometheus exporter 啟動: http://localhost:{self.port}/metrics")
    
    def stop_server(self):
        """停止 HTTP 服務器"""
        if self._server:
            self._server.shutdown()
            self._server = None
            self._thread = None
    
    def get_status(self) -> Dict[str, Any]:
        """獲取狀態"""
        return {
            "running": self._server is not None,
            "port": self.port,
            "counters": len(self._counters),
            "gauges": len(self._gauges)
        }


# 全局實例
exporter = SimplePrometheusExporter()


# ============== 使用示例 ==============

if __name__ == "__main__":
    print("=" * 50)
    print("📊 Prometheus Exporter Test (Simple)")
    print("=" * 50)
    
    # 記錄一些指標
    print("\n📝 記錄指標...")
    
    exporter.record_request("gpt-4o", True, 1500)
    exporter.record_request("gpt-4o", True, 1200)
    exporter.record_request("gpt-4o-mini", True, 300)
    exporter.record_request("claude-3", False, 5000)
    
    exporter.record_cost("gpt-4o", 0.03)
    exporter.record_cost("gpt-4o", 0.025)
    exporter.record_cost("gpt-4o-mini", 0.002)
    
    exporter.record_cache_hit(True)
    exporter.record_cache_hit(False)
    
    exporter.record_failover("gpt-4o", "gpt-4o-mini")
    
    # 獲取指標
    print("\n📥 獲取指標 (Prometheus 格式):")
    print(exporter.get_metrics())
    
    # 狀態
    print("📊 狀態:")
    status = exporter.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print("\n✅ 測試完成!")
