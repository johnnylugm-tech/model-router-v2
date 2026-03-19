#!/usr/bin/env python3
"""
Batch Processor - 請求批處理

功能：
- 合併多個請求
- 並行處理
- 結果聚合
"""

import asyncio
import time
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json


@dataclass
class BatchRequest:
    """批處理請求"""
    id: str
    prompt: str
    model: str = "gpt-4o-mini"
    metadata: Dict = field(default_factory=dict)
    

@dataclass
class BatchResponse:
    """批處理響應"""
    request_id: str
    response: str
    model: str
    duration_ms: int
    success: bool
    error: str = None


class BatchProcessor:
    """請求批處理器"""
    
    def __init__(
        self,
        max_concurrent: int = 5,
        batch_size: int = 10,
        timeout: int = 60
    ):
        """
        初始化批處理器
        
        Args:
            max_concurrent: 最大並行數
            batch_size: 批次大小
            timeout: 超時時間（秒）
        """
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        
        # 請求隊列
        self.queue: List[BatchRequest] = []
        
        # 緩衝計時器
        self._buffer_timer = None
        self._buffer_duration = 1.0  # 1秒緩衝
    
    def add(self, request: BatchRequest):
        """添加請求到隊列"""
        self.queue.append(request)
        
        # 如果達到批次大小，立即處理
        if len(self.queue) >= self.batch_size:
            return self.process()
        
        # 否則，啟動緩衝計時器
        if not self._buffer_timer:
            self._buffer_timer = time.time()
    
    def process(self) -> List[BatchResponse]:
        """處理當前隊列中的所有請求"""
        if not self.queue:
            return []
        
        # 獲取當前批次
        batch = self.queue[:self.batch_size]
        self.queue = self.queue[self.batch_size:]
        
        # 並行處理
        responses = []
        
        # 這裡模擬實際 API 調用
        # 實際使用時替換為真正的 API 調用
        futures = []
        for req in batch:
            future = self.executor.submit(self._process_single, req)
            futures.append(future)
        
        # 收集結果
        for future in as_completed(futures, timeout=self.timeout):
            try:
                response = future.result()
                responses.append(response)
            except Exception as e:
                responses.append(BatchResponse(
                    request_id="unknown",
                    response="",
                    model="",
                    duration_ms=0,
                    success=False,
                    error=str(e)
                ))
        
        return responses
    
    def _process_single(self, request: BatchRequest) -> BatchResponse:
        """處理單個請求"""
        start = time.time()
        
        # 模擬 API 調用
        # 實際使用時替換為真正的 API 調用
        try:
            # 這裡調用實際的 LLM API
            response_text = f"Response to: {request.prompt[:50]}..."
            
            duration = int((time.time() - start) * 1000)
            
            return BatchResponse(
                request_id=request.id,
                response=response_text,
                model=request.model,
                duration_ms=duration,
                success=True
            )
        except Exception as e:
            return BatchResponse(
                request_id=request.id,
                response="",
                model=request.model,
                duration_ms=int((time.time() - start) * 1000),
                success=False,
                error=str(e)
            )
    
    def process_all(self) -> List[BatchResponse]:
        """處理所有剩餘請求"""
        all_responses = []
        
        while self.queue:
            responses = self.process()
            all_responses.extend(responses)
        
        return all_responses
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        return {
            "queue_size": len(self.queue),
            "max_concurrent": self.max_concurrent,
            "batch_size": self.batch_size,
            "timeout": self.timeout
        }
    
    def close(self):
        """關閉執行器"""
        self.executor.shutdown(wait=True)


# ============== 使用示例 ==============

if __name__ == "__main__":
    print("=" * 50)
    print("📦 Batch Processor Test")
    print("=" * 50)
    
    # 創建處理器
    processor = BatchProcessor(
        max_concurrent=3,
        batch_size=5,
        timeout=30
    )
    
    # 添加請求
    print("\n📝 添加請求...")
    for i in range(12):
        req = BatchRequest(
            id=f"req-{i}",
            prompt=f"測試請求 {i}: 請回答這個問題",
            model="gpt-4o-mini"
        )
        processor.add(req)
    
    # 處理
    print("\n🔄 處理請求...")
    responses = processor.process_all()
    
    # 結果
    print(f"\n📊 處理了 {len(responses)} 個請求")
    for resp in responses:
        status = "✅" if resp.success else "❌"
        print(f"   {status} {resp.request_id}: {resp.duration_ms}ms")
    
    # 統計
    print("\n📈 統計:")
    stats = processor.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    processor.close()
    print("\n✅ 測試完成!")
