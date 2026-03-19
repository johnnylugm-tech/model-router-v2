#!/usr/bin/env python3
"""
Model Router - 負載測試

效能測試腳本
"""

import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List

# 模擬請求
def mock_request(i: int) -> dict:
    """模擬一次請求"""
    start = time.time()
    
    # 模擬延遲 (50-200ms)
    time.sleep(0.05 + (i % 150) / 1000)
    
    latency = (time.time() - start) * 1000
    
    return {
        "id": i,
        "latency_ms": latency,
        "success": True
    }


@dataclass
class LoadTestResult:
    """負載測試結果"""
    total_requests: int
    successful: int
    failed: int
    duration_seconds: float
    qps: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


def run_load_test(
    num_requests: int = 100,
    concurrency: int = 10,
    warmup: int = 10
) -> LoadTestResult:
    """執行負載測試"""
    
    print(f"\n🚀 開始負載測試")
    print(f"   請求數: {num_requests}")
    print(f"   並發數: {concurrency}")
    print(f"   預熱: {warmup}")
    
    # 預熱
    print(f"\n🔥 預熱中...")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(mock_request, i) for i in range(warmup)]
        for f in as_completed(futures):
            f.result()
    
    # 正式測試
    print(f"⚡ 執行測試...")
    latencies = []
    successful = 0
    failed = 0
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(mock_request, i) for i in range(num_requests)]
        
        for f in as_completed(futures):
            try:
                result = f.result()
                latencies.append(result["latency_ms"])
                successful += 1
            except Exception:
                failed += 1
    
    duration = time.time() - start_time
    
    # 計算統計
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    
    result = LoadTestResult(
        total_requests=num_requests,
        successful=successful,
        failed=failed,
        duration_seconds=duration,
        qps=num_requests / duration,
        avg_latency_ms=statistics.mean(latencies),
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        p99_latency_ms=p99
    )
    
    return result


def print_result(result: LoadTestResult):
    """打印結果"""
    print("\n" + "=" * 50)
    print("📊 負載測試結果")
    print("=" * 50)
    
    print(f"\n📈 吞吐量")
    print(f"   總請求數: {result.total_requests}")
    print(f"   成功: {result.successful}")
    print(f"   失敗: {result.failed}")
    print(f"   耗時: {result.duration_seconds:.2f}s")
    print(f"   QPS: {result.qps:.2f}")
    
    print(f"\n⏱️ 延遲")
    print(f"   平均: {result.avg_latency_ms:.2f}ms")
    print(f"   P50:  {result.p50_latency_ms:.2f}ms")
    print(f"   P95:  {result.p95_latency_ms:.2f}ms")
    print(f"   P99:  {result.p99_latency_ms:.2f}ms")
    
    print("\n" + "=" * 50)


# 測試場景
scenarios = [
    {"name": "輕量負載", "requests": 100, "concurrency": 5, "warmup": 10},
    {"name": "中等負載", "requests": 500, "concurrency": 20, "warmup": 50},
    {"name": "高負載", "requests": 1000, "concurrency": 50, "warmup": 100},
]


if __name__ == "__main__":
    print("=" * 50)
    print("⚡ Model Router 負載測試")
    print("=" * 50)
    
    for scenario in scenarios:
        print(f"\n\n{'='*50}")
        print(f"📋 場景: {scenario['name']}")
        print(f"{'='*50}")
        
        result = run_load_test(
            num_requests=scenario["requests"],
            concurrency=scenario["concurrency"],
            warmup=scenario["warmup"]
        )
        
        print_result(result)
    
    print("\n\n✅ 負載測試完成!")
    print("\n📝 生產環境建議:")
    print("   - 輕量: QPS < 50, 延遲 < 200ms")
    print("   - 中等: QPS < 200, 延遲 < 500ms")
    print("   - 高負載: 需要更多優化或分散式部署")
