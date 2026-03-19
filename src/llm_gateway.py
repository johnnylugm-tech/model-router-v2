#!/usr/bin/env python3
"""
LLM Gateway - API 閘道

功能：
- 統一 API 端點
- 請求轉發
- 認證管理
- 流量控制
"""

import time
import json
import hashlib
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from flask import Flask, request, jsonify
from threading import Thread

# 导入 Model Router 核心模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.semantic_cache import SemanticCache
from src.rate_limiter import RateLimiter, RateLimit, Quota
from src.audit_logger import AuditLogger, AuditAction


@dataclass
class APIKey:
    """API Key"""
    key: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    is_active: bool = True
    daily_limit: int = 10000
    rate_limit: int = 60  # 每分鐘


@dataclass
class GatewayConfig:
    """閘道配置"""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    require_auth: bool = True
    rate_limit_minute: int = 60
    rate_limit_hour: int = 1000
    rate_limit_day: int = 10000


class LLMGateway:
    """LLM API 閘道"""
    
    def __init__(
        self,
        config: GatewayConfig = None,
        router=None
    ):
        """
        初始化 LLM Gateway
        
        Args:
            config: 閘道配置
            router: Model Router 實例
        """
        self.config = config or GatewayConfig()
        self.router = router
        
        # Flask 應用
        self.app = Flask(__name__)
        self._setup_routes()
        
        # 組件
        self.cache = SemanticCache(similarity_threshold=0.9)
        self.rate_limiter = RateLimiter(
            rate_limit=RateLimit(
                requests_per_minute=self.config.rate_limit_minute,
                requests_per_hour=self.config.rate_limit_hour,
                requests_per_day=self.config.rate_limit_day
            ),
            quota=Quota(daily_limit=100000)
        )
        self.audit_logger = AuditLogger()
        
        # API Key 存儲
        self.api_keys: Dict[str, APIKey] = {}
        
        # 統計
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_cost": 0.0
        }
    
    def _setup_routes(self):
        """設置路由"""
        
        @self.app.route("/health", methods=["GET"])
        def health():
            """健康檢查"""
            return jsonify({
                "status": "healthy",
                "timestamp": time.time()
            })
        
        @self.app.route("/v1/chat/completions", methods=["POST"])
        def chat_completions():
            """統一的 Chat Completions API"""
            return self._handle_chat_completions()
        
        @self.app.route("/v1/models", methods=["GET"])
        def list_models():
            """列出可用模型"""
            if self.router:
                models = self.router.list_models()
            else:
                models = self._default_models()
            
            return jsonify({
                "object": "list",
                "data": models
            })
        
        @self.app.route("/v1/models/<model_id>", methods=["GET"])
        def get_model(model_id):
            """獲取模型信息"""
            if self.router:
                model = self.router.get_model(model_id)
            else:
                model = self._get_default_model(model_id)
            
            if model:
                return jsonify(model)
            return jsonify({"error": "Model not found"}), 404
        
        @self.app.route("/v1/keys", methods=["POST"])
        def create_api_key():
            """創建 API Key"""
            data = request.json or {}
            user_id = data.get("user_id", "default")
            
            key = self._create_api_key(user_id)
            
            return jsonify({
                "key": key,
                "user_id": user_id,
                "created_at": time.time()
            })
        
        @self.app.route("/v1/stats", methods=["GET"])
        def get_stats():
            """獲取統計"""
            return jsonify(self._stats)
        
        @self.app.route("/v1/usage", methods=["GET"])
        def get_usage():
            """獲取使用情況"""
            api_key = self._get_api_key_from_header()
            if not api_key:
                return jsonify({"error": "API key required"}), 401
            
            usage = self._get_usage(api_key)
            return jsonify(usage)
        
        @self.app.errorhandler(404)
        def not_found(e):
            return jsonify({"error": "Not found"}), 404
        
        @self.app.errorhandler(500)
        def server_error(e):
            return jsonify({"error": "Internal server error"}), 500
    
    def _handle_chat_completions(self):
        """處理 Chat Completions 請求"""
        self._stats["total_requests"] += 1
        
        # 認證
        if self.config.require_auth:
            api_key = self._get_api_key_from_header()
            if not api_key:
                self._stats["failed_requests"] += 1
                return jsonify({"error": "API key required"}), 401
            
            # 驗證 API Key
            if not self._validate_api_key(api_key):
                self._stats["failed_requests"] += 1
                return jsonify({"error": "Invalid API key"}), 403
            
            # Rate Limit
            rate_result = self.rate_limiter.check(api_key.user_id)
            if not rate_result["allowed"]:
                self._stats["failed_requests"] += 1
                return jsonify({
                    "error": "Rate limit exceeded",
                    "retry_after": rate_result["next_available_in"]
                }), 429
        
        # 解析請求
        data = request.json or {}
        model = data.get("model")
        messages = data.get("messages", [])
        
        if not model:
            return jsonify({"error": "model is required"}), 400
        
        if not messages:
            return jsonify({"error": "messages is required"}), 400
        
        # 構建 prompt
        prompt = self._messages_to_prompt(messages)
        
        # 記錄審計日誌
        self.audit_logger.log(
            action=AuditAction.REQUEST.value,
            user_id=api_key.user_id if api_key else "anonymous",
            model=model,
            details={"prompt": prompt[:100]}
        )
        
        # 檢查快取
        cached = self.cache.get(prompt)
        if cached:
            self._stats["cache_hits"] += 1
            return jsonify(cached)
        
        # 調用 Model Router
        try:
            if self.router:
                result = self.router.route(
                    task=prompt,
                    model=model,
                    budget=data.get("budget", "balanced")
                )
            else:
                result = self._mock_response(model, prompt)
            
            self._stats["successful_requests"] += 1
            
            # 轉換為 OpenAI 格式
            response = self._to_openai_format(model, result)
            
            # 存入快取
            self.cache.set(prompt, response)
            
            return jsonify(response)
            
        except Exception as e:
            self._stats["failed_requests"] += 1
            self.audit_logger.log(
                action=AuditAction.REQUEST.value,
                level="error",
                user_id=api_key.user_id if api_key else "anonymous",
                model=model,
                details={"error": str(e)},
                success=False
            )
            return jsonify({"error": str(e)}), 500
    
    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """將 messages 轉換為 prompt"""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        return "\n".join(parts)
    
    def _to_openai_format(self, model: str, result: Any) -> Dict:
        """轉換為 OpenAI 格式"""
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.get("content", "") if isinstance(result, dict) else str(result)
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
    
    def _default_models(self) -> List[Dict]:
        """默認模型列表"""
        return [
            {
                "id": "gpt-4o",
                "object": "model",
                "created": 2024,
                "owned_by": "openai"
            },
            {
                "id": "claude-3-5-sonnet",
                "object": "model",
                "created": 2024,
                "owned_by": "anthropic"
            },
            {
                "id": "gemini-1.5-flash",
                "object": "model",
                "created": 2024,
                "owned_by": "google"
            }
        ]
    
    def _get_default_model(self, model_id: str) -> Optional[Dict]:
        """獲取默認模型"""
        models = self._default_models()
        for m in models:
            if m["id"] == model_id:
                return m
        return None
    
    def _mock_response(self, model: str, prompt: str) -> Dict:
        """Mock 響應（用於測試）"""
        return {
            "content": f"Mock response for: {prompt[:50]}...",
            "model": model
        }
    
    def _get_api_key_from_header(self) -> Optional[APIKey]:
        """從 header 獲取 API Key"""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth[7:]
            return self.api_keys.get(key)
        return None
    
    def _create_api_key(self, user_id: str) -> str:
        """創建 API Key"""
        key = f"mr_{uuid.uuid4().hex}"
        self.api_keys[key] = APIKey(
            key=key,
            user_id=user_id
        )
        return key
    
    def _validate_api_key(self, api_key: APIKey) -> bool:
        """驗證 API Key"""
        return api_key is not None and api_key.is_active
    
    def _get_usage(self, api_key: APIKey) -> Dict:
        """獲取使用情況"""
        stats = self.rate_limiter.get_stats()
        return {
            "user_id": api_key.user_id,
            "daily_limit": api_key.daily_limit,
            "requests_today": stats["current"]["day"]
        }
    
    def run(self):
        """啟動 Gateway"""
        print(f"🚀 LLM Gateway 啟動: http://{self.config.host}:{self.config.port}")
        print(f"   API 端點: /v1/chat/completions")
        print(f"   模型列表: /v1/models")
        
        self.app.run(
            host=self.config.host,
            port=self.config.port,
            debug=self.config.debug
        )
    
    def run_background(self):
        """後台啟動"""
        thread = Thread(target=self.run, daemon=True)
        thread.start()
        return self


# ============== 使用示例 ==============

if __name__ == "__main__":
    print("=" * 50)
    print("🌐 LLM Gateway Test")
    print("=" * 50)
    
    # 創建 Gateway
    gateway = LLMGateway(
        config=GatewayConfig(
            host="0.0.0.0",
            port=8080,
            debug=True,
            require_auth=False  # 測試時關閉認證
        )
    )
    
    # 啟動
    gateway.run()
