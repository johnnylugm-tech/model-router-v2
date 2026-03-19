"""
API 客戶端 - Unified API Client
支援 OpenAI / Anthropic / MiniMax / Gemini
標準化的錯誤處理
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import os
import time
import logging
import json


# 異常定義
class APIError(Exception):
    """API 錯誤基類"""
    def __init__(self, message: str, provider: str = None, code: str = None):
        self.message = message
        self.provider = provider
        self.code = code
        super().__init__(f"[{provider or 'Unknown'}] {message}")


class AuthenticationError(APIError):
    """認證錯誤"""
    pass


class RateLimitError(APIError):
    """速率限制錯誤"""
    def __init__(self, message: str, provider: str = None, retry_after: int = None):
        super().__init__(message, provider, "rate_limit")
        self.retry_after = retry_after


class InvalidRequestError(APIError):
    """無效請求錯誤"""
    pass


class ModelNotFoundError(APIError):
    """模型未找到錯誤"""
    pass


class TimeoutError(APIError):
    """超時錯誤"""
    pass


# 響應數據類
@dataclass
class CompletionResponse:
    """補全響應"""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    raw_response: Dict[str, Any]


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    provider: str
    context_window: int
    supports_streaming: bool = True


# 基礎客戶端接口
class BaseAPIClient(ABC):
    """API 客戶端基類"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or self._get_api_key()
        self.base_url = base_url
        self.logger = logging.getLogger(self.__class__.__name__)
        self._request_count = 0
        self._error_count = 0
    
    @abstractmethod
    def _get_api_key(self) -> str:
        """獲取 API Key"""
        pass
    
    @abstractmethod
    def complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> CompletionResponse:
        """完成請求"""
        pass
    
    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """列出可用模型"""
        pass
    
    def get_stats(self) -> Dict[str, int]:
        """獲取統計"""
        return {
            "requests": self._request_count,
            "errors": self._error_count
        }


# OpenAI 客戶端
class OpenAIClient(BaseAPIClient):
    """OpenAI API 客戶端"""
    
    def _get_api_key(self) -> str:
        return os.environ.get("OPENAI_API_KEY", "")
    
    def __init__(self, api_key: str = None, base_url: str = None):
        super().__init__(api_key, base_url or "https://api.openai.com/v1")
        self.provider = "openai"
    
    def complete(
        self,
        prompt: str,
        model: str = "gpt-4o",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> CompletionResponse:
        """發送補全請求到 OpenAI"""
        self._request_count += 1
        start_time = time.time()
        
        try:
            # 模擬請求 (實際需要調用真實 API)
            # 這裡為了演示，返回模擬響應
            response_content = f"[OpenAI {model}] 回覆: {prompt[:50]}..."
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return CompletionResponse(
                content=response_content,
                model=model,
                provider=self.provider,
                input_tokens=len(prompt) // 4,
                output_tokens=len(response_content) // 4,
                latency_ms=latency_ms,
                raw_response={"model": model, "choices": [{"message": {"content": response_content}}]}
            )
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"OpenAI API 錯誤: {e}")
            raise APIError(str(e), self.provider)
    
    def list_models(self) -> List[ModelInfo]:
        """列出 OpenAI 可用模型"""
        return [
            ModelInfo("gpt-4o", "GPT-4o", "openai", 128000),
            ModelInfo("gpt-4o-mini", "GPT-4o Mini", "openai", 128000),
            ModelInfo("gpt-4-turbo", "GPT-4 Turbo", "openai", 128000),
            ModelInfo("gpt-3.5-turbo", "GPT-3.5 Turbo", "openai", 16385),
        ]


# Anthropic 客戶端
class AnthropicClient(BaseAPIClient):
    """Anthropic API 客戶端"""
    
    def _get_api_key(self) -> str:
        return os.environ.get("ANTHROPIC_API_KEY", "")
    
    def __init__(self, api_key: str = None, base_url: str = None):
        super().__init__(api_key, base_url or "https://api.anthropic.com")
        self.provider = "anthropic"
    
    def complete(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> CompletionResponse:
        """發送補全請求到 Anthropic"""
        self._request_count += 1
        start_time = time.time()
        
        try:
            response_content = f"[Anthropic {model}] 回覆: {prompt[:50]}..."
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return CompletionResponse(
                content=response_content,
                model=model,
                provider=self.provider,
                input_tokens=len(prompt) // 4,
                output_tokens=len(response_content) // 4,
                latency_ms=latency_ms,
                raw_response={"model": model, "content": response_content}
            )
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Anthropic API 錯誤: {e}")
            raise APIError(str(e), self.provider)
    
    def list_models(self) -> List[ModelInfo]:
        """列出 Anthropic 可用模型"""
        return [
            ModelInfo("claude-sonnet-4-20250514", "Claude Sonnet 4", "anthropic", 200000),
            ModelInfo("claude-opus-4-20250514", "Claude Opus 4", "anthropic", 200000),
            ModelInfo("claude-3-5-sonnet-20240620", "Claude 3.5 Sonnet", "anthropic", 200000),
            ModelInfo("claude-3-haiku-20240307", "Claude 3 Haiku", "anthropic", 200000),
        ]


# MiniMax 客戶端
class MiniMaxClient(BaseAPIClient):
    """MiniMax API 客戶端"""
    
    def _get_api_key(self) -> str:
        return os.environ.get("MINIMAX_API_KEY", "")
    
    def __init__(self, api_key: str = None, base_url: str = None):
        super().__init__(api_key, base_url or "https://api.minimax.chat/v1")
        self.provider = "minimax"
    
    def complete(
        self,
        prompt: str,
        model: str = "abab6.5s-chat",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> CompletionResponse:
        """發送補全請求到 MiniMax"""
        self._request_count += 1
        start_time = time.time()
        
        try:
            response_content = f"[MiniMax {model}] 回覆: {prompt[:50]}..."
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return CompletionResponse(
                content=response_content,
                model=model,
                provider=self.provider,
                input_tokens=len(prompt) // 4,
                output_tokens=len(response_content) // 4,
                latency_ms=latency_ms,
                raw_response={"model": model, "choices": [{"message": {"content": response_content}}]}
            )
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"MiniMax API 錯誤: {e}")
            raise APIError(str(e), self.provider)
    
    def list_models(self) -> List[ModelInfo]:
        """列出 MiniMax 可用模型"""
        return [
            ModelInfo("abab6.5s-chat", "MiniMax Abab 6.5s", "minimax", 245760),
            ModelInfo("abab6.5g-chat", "MiniMax Abab 6.5g", "minimax", 245760),
            ModelInfo("abab5.5s-chat", "MiniMax Abab 5.5s", "minimax", 128000),
        ]


# Gemini 客戶端
class GeminiClient(BaseAPIClient):
    """Google Gemini API 客戶端"""
    
    def _get_api_key(self) -> str:
        return os.environ.get("GEMINI_API_KEY", "")
    
    def __init__(self, api_key: str = None, base_url: str = None):
        super().__init__(api_key, base_url or "https://generativelanguage.googleapis.com/v1beta")
        self.provider = "gemini"
    
    def complete(
        self,
        prompt: str,
        model: str = "gemini-2.0-flash",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> CompletionResponse:
        """發送補全請求到 Gemini"""
        self._request_count += 1
        start_time = time.time()
        
        try:
            response_content = f"[Gemini {model}] 回覆: {prompt[:50]}..."
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return CompletionResponse(
                content=response_content,
                model=model,
                provider=self.provider,
                input_tokens=len(prompt) // 4,
                output_tokens=len(response_content) // 4,
                latency_ms=latency_ms,
                raw_response={"model": model, "candidates": [{"content": {"parts": [{"text": response_content}]}}]}
            )
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Gemini API 錯誤: {e}")
            raise APIError(str(e), self.provider)
    
    def list_models(self) -> List[ModelInfo]:
        """列出 Gemini 可用模型"""
        return [
            ModelInfo("gemini-2.0-flash", "Gemini 2.0 Flash", "gemini", 1048576),
            ModelInfo("gemini-1.5-pro", "Gemini 1.5 Pro", "gemini", 2097152),
            ModelInfo("gemini-1.5-flash", "Gemini 1.5 Flash", "gemini", 1048576),
            ModelInfo("gemini-1.5-flash-8b", "Gemini 1.5 Flash 8B", "gemini", 1048576),
        ]


# 統一工廠
class APIClientFactory:
    """API 客戶端工廠"""
    
    _clients: Dict[str, BaseAPIClient] = {}
    
    @classmethod
    def get_client(
        cls, 
        provider: str, 
        api_key: str = None,
        base_url: str = None
    ) -> BaseAPIClient:
        """
        獲取 API 客戶端
        
        Args:
            provider: 提供商名稱 (openai, anthropic, minimax, gemini)
            api_key: API Key
            base_url: 自定義 Base URL
            
        Returns:
            BaseAPIClient: API 客戶端實例
        """
        provider = provider.lower()
        
        if provider in cls._clients:
            return cls._clients[provider]
        
        clients_map = {
            "openai": OpenAIClient,
            "anthropic": AnthropicClient,
            "minimax": MiniMaxClient,
            "gemini": GeminiClient,
        }
        
        if provider not in clients_map:
            raise ValueError(f"不支持的提供商: {provider}")
        
        client = clients_map[provider](api_key, base_url)
        cls._clients[provider] = client
        return client
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """列出支持的提供商"""
        return ["openai", "anthropic", "minimax", "gemini"]
    
    @classmethod
    def clear_cache(cls) -> None:
        """清除客戶端緩存"""
        cls._clients.clear()


# 測試函數
def test_api_client(provider: str) -> Dict[str, Any]:
    """
    測試 API 客戶端
    
    Args:
        provider: 提供商名稱
        
    Returns:
        Dict: 測試結果
    """
    try:
        client = APIClientFactory.get_client(provider)
        models = client.list_models()
        
        return {
            "status": "success",
            "provider": provider,
            "models": [
                {
                    "id": m.id,
                    "name": m.name,
                    "context_window": m.context_window
                }
                for m in models
            ],
            "stats": client.get_stats()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "provider": provider,
            "error": str(e)
        }
