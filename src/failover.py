"""
Failover Module - 自動 Failover 系統
自動偵測 API 錯誤、切換到 Fallback Provider、支援 RateLimit 重試
"""

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any, Dict
from abc import ABC, abstractmethod


class ErrorLevel(Enum):
    """錯誤等級"""
    L1_INPUT = "L1_INPUT"          # 輸入錯誤 - 不應重試
    L2_API = "L2_API"              # API 錯誤 - 可重試
    L3_RATE_LIMIT = "L3_RATE_LIMIT"  # Rate Limit - 應該等待後重試
    L4_EXECUTION = "L4_EXECUTION" # 執行錯誤 - 可重試有限次
    L5_SYSTEM = "L5_SYSTEM"       # 系統錯誤 - 熔斷


class APIError(Exception):
    """API 錯誤基類"""
    def __init__(
        self,
        message: str,
        level: ErrorLevel,
        recoverable: bool = True,
        provider: Optional[str] = None,
        model_id: Optional[str] = None,
        status_code: Optional[int] = None
    ):
        self.message = message
        self.level = level
        self.recoverable = recoverable
        self.provider = provider
        self.model_id = model_id
        self.status_code = status_code
        super().__init__(f"[{level.value}] {message}")


class RateLimitError(APIError):
    """Rate Limit 錯誤"""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        provider: Optional[str] = None,
        model_id: Optional[str] = None,
        retry_after: Optional[float] = None
    ):
        super().__init__(
            message=message,
            level=ErrorLevel.L3_RATE_LIMIT,
            recoverable=True,
            provider=provider,
            model_id=model_id
        )
        self.retry_after = retry_after or 60.0


class AuthenticationError(APIError):
    """認證錯誤"""
    def __init__(self, message: str = "Authentication failed", provider: Optional[str] = None):
        super().__init__(
            message=message,
            level=ErrorLevel.L1_INPUT,
            recoverable=False,
            provider=provider
        )


class InvalidRequestError(APIError):
    """無效請求錯誤"""
    def __init__(self, message: str = "Invalid request", provider: Optional[str] = None):
        super().__init__(
            message=message,
            level=ErrorLevel.L1_INPUT,
            recoverable=False,
            provider=provider
        )


class TimeoutError(APIError):
    """超時錯誤"""
    def __init__(
        self,
        message: str = "Request timeout",
        provider: Optional[str] = None,
        model_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            level=ErrorLevel.L4_EXECUTION,
            recoverable=True,
            provider=provider,
            model_id=model_id
        )


class ModelNotFoundError(APIError):
    """模型不存在錯誤"""
    def __init__(self, message: str = "Model not found", model_id: Optional[str] = None):
        super().__init__(
            message=message,
            level=ErrorLevel.L1_INPUT,
            recoverable=False,
            model_id=model_id
        )


class AllProvidersFailedError(Exception):
    """所有 Provider 都失敗"""
    def __init__(self, errors: List[APIError] = None):
        self.errors = errors or []
        message = "All providers failed. Errors:\n" + "\n".join(
            f"  - {e.level.value}: {e.message}" for e in self.errors
        )
        super().__init__(message)


@dataclass
class FailoverConfig:
    """Failover 配置"""
    enabled: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_retries: int = 5
    rate_limit_backoff: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0


@dataclass
class ProviderState:
    """Provider 狀態"""
    name: str
    error_count: int = 0
    success_count: int = 0
    last_error_time: Optional[float] = None
    is_healthy: bool = True
    break_until: Optional[float] = None
    
    def record_success(self) -> None:
        """記錄成功"""
        self.success_count += 1
        self.error_count = 0
        self.is_healthy = True
    
    def record_error(self, error: APIError) -> None:
        """記錄錯誤"""
        self.error_count += 1
        self.last_error_time = time.time()
        
        if isinstance(error, RateLimitError):
            # Rate Limit 特殊處理
            if error.retry_after:
                self.break_until = time.time() + error.retry_after
    
    def is_available(self) -> bool:
        """是否可用"""
        if not self.is_healthy:
            return False
        if self.break_until and time.time() < self.break_until:
            return False
        return True


class FailoverStrategy(ABC):
    """Failover 策略抽象類"""
    
    @abstractmethod
    def get_next_provider(
        self,
        providers: List[str],
        states: Dict[str, ProviderState],
        last_error: Optional[APIError] = None
    ) -> Optional[str]:
        """獲取下一個 Provider"""
        pass


class SequentialFailoverStrategy(FailoverStrategy):
    """順序 Failover 策略"""
    
    def get_next_provider(
        self,
        providers: List[str],
        states: Dict[str, ProviderState],
        last_error: Optional[APIError] = None
    ) -> Optional[str]:
        for provider in providers:
            if states.get(provider, ProviderState(provider)).is_available():
                return provider
        return None


class PriorityFailoverStrategy(FailoverStrategy):
    """優先級 Failover 策略"""
    
    def __init__(self, priority_map: Dict[str, int] = None):
        self.priority_map = priority_map or {}
    
    def get_next_provider(
        self,
        providers: List[str],
        states: Dict[str, ProviderState],
        last_error: Optional[APIError] = None
    ) -> Optional[str]:
        # 按優先級排序
        sorted_providers = sorted(
            providers,
            key=lambda p: self.priority_map.get(p, 100)
        )
        
        for provider in sorted_providers:
            if states.get(provider, ProviderState(provider)).is_available():
                return provider
        return None


class AutoFailoverRouter:
    """
    自動 Failover 路由器
    
    功能:
    - 自動偵測 API 錯誤
    - 自動切換到 Fallback Provider
    - 支援 RateLimit 重試
    - 完整的錯誤分類 (L1-L5)
    - 熔斷機制
    """
    
    def __init__(
        self,
        config: Optional[FailoverConfig] = None,
        strategy: Optional[FailoverStrategy] = None
    ):
        self.config = config or FailoverConfig()
        self.strategy = strategy or SequentialFailoverStrategy()
        self.logger = logging.getLogger(__name__)
        
        # Provider 狀態追蹤
        self._states: Dict[str, ProviderState] = {}
        
        # 錯誤分類器
        self._error_classifier = ErrorClassifier()
    
    def _get_or_create_state(self, provider: str) -> ProviderState:
        """獲取或創建 Provider 狀態"""
        if provider not in self._states:
            self._states[provider] = ProviderState(name=provider)
        return self._states[provider]
    
    def _classify_error(self, error: Exception) -> APIError:
        """分類錯誤"""
        return self._error_classifier.classify(error)
    
    def _should_retry(self, error: APIError, retry_count: int) -> bool:
        """判斷是否應該重試"""
        if not self.config.enabled:
            return False
        
        if not error.recoverable:
            return False
        
        if isinstance(error, RateLimitError):
            return retry_count < self.config.rate_limit_retries
        
        return retry_count < self.config.max_retries
    
    def _get_retry_delay(self, error: APIError, retry_count: int) -> float:
        """計算重試延遲"""
        if isinstance(error, RateLimitError) and error.retry_after:
            return error.retry_after
        
        if isinstance(error, RateLimitError):
            return self.config.retry_delay * (self.config.rate_limit_backoff ** retry_count)
        
        return self.config.retry_delay * (2 ** retry_count)
    
    def route_with_failover(
        self,
        task: Any,
        providers: List[str],
        call_func: Callable[[str, Any], Any]
    ) -> Any:
        """
        使用 Failover 進行路由
        
        Args:
            task: 任務內容
            providers: Provider 列表 (按優先級排序)
            call_func: 調用函數，簽名: call_func(provider, task) -> result
            
        Returns:
            Any: 執行結果
            
        Raises:
            AllProvidersFailedError: 所有 Provider 都失敗
        """
        errors: List[APIError] = []
        last_error: Optional[APIError] = None
        
        for attempt in range(self.config.max_retries + self.config.rate_limit_retries + 1):
            # 獲取下一個可用的 Provider
            provider = self.strategy.get_next_provider(
                providers,
                self._states,
                last_error
            )
            
            if not provider:
                break
            
            state = self._get_or_create_state(provider)
            
            try:
                self.logger.info(f"Attempting provider: {provider} (attempt {attempt + 1})")
                result = call_func(provider, task)
                
                # 記錄成功
                state.record_success()
                self.logger.info(f"Provider {provider} succeeded")
                return result
                
            except Exception as e:
                # 分類錯誤
                api_error = self._classify_error(e)
                api_error.provider = provider
                
                self.logger.warning(
                    f"Provider {provider} failed: {api_error.level.value} - {api_error.message}"
                )
                
                # 記錄錯誤
                state.record_error(api_error)
                errors.append(api_error)
                last_error = api_error
                
                # 判斷是否應該重試
                if not self._should_retry(api_error, attempt):
                    self.logger.info(f"Should not retry after error: {api_error.level.value}")
                    break
                
                # 等待後重試
                delay = self._get_retry_delay(api_error, attempt)
                self.logger.info(f"Retrying in {delay:.2f}s...")
                time.sleep(delay)
        
        # 所有 Provider 都失敗
        raise AllProvidersFailedError(errors)
    
    def get_provider_status(self) -> Dict[str, Dict]:
        """獲取 Provider 狀態"""
        return {
            name: {
                "error_count": state.error_count,
                "success_count": state.success_count,
                "is_healthy": state.is_available(),
                "last_error_time": state.last_error_time
            }
            for name, state in self._states.items()
        }
    
    def reset_provider(self, provider: str) -> None:
        """重置 Provider 狀態"""
        if provider in self._states:
            self._states[provider] = ProviderState(name=provider)
    
    def reset_all(self) -> None:
        """重置所有 Provider"""
        self._states.clear()


class ErrorClassifier:
    """錯誤分類器"""
    
    # 錯誤關鍵詞映射
    ERROR_PATTERNS = {
        # Rate Limit
        "rate_limit": RateLimitError,
        "rate limit": RateLimitError,
        "429": RateLimitError,
        "too many requests": RateLimitError,
        "quota": RateLimitError,
        
        # Authentication
        "authentication": AuthenticationError,
        "unauthorized": AuthenticationError,
        "401": AuthenticationError,
        "api key": AuthenticationError,
        "invalid api key": AuthenticationError,
        
        # Invalid Request
        "invalid request": InvalidRequestError,
        "400": InvalidRequestError,
        "bad request": InvalidRequestError,
        "validation": InvalidRequestError,
        
        # Timeout
        "timeout": TimeoutError,
        "timed out": TimeoutError,
        "504": TimeoutError,
        
        # Model Not Found
        "model not found": ModelNotFoundError,
        "404": ModelNotFoundError,
        "model does not exist": ModelNotFoundError,
    }
    
    def classify(self, error: Exception) -> APIError:
        """分類錯誤"""
        error_msg = str(error).lower()
        
        # 檢查錯誤模式
        for pattern, error_class in self.ERROR_PATTERNS.items():
            if pattern in error_msg:
                if error_class == RateLimitError:
                    # 嘗試提取 retry_after
                    retry_after = self._extract_retry_after(error)
                    return RateLimitError(
                        message=str(error),
                        retry_after=retry_after
                    )
                elif error_class == AuthenticationError:
                    return AuthenticationError(str(error))
                elif error_class == InvalidRequestError:
                    return InvalidRequestError(str(error))
                elif error_class == TimeoutError:
                    return TimeoutError(str(error))
                elif error_class == ModelNotFoundError:
                    return ModelNotFoundError(str(error))
        
        # 默認認為是 API 錯誤
        return APIError(
            message=str(error),
            level=ErrorLevel.L2_API,
            recoverable=True
        )
    
    def _extract_retry_after(self, error: Exception) -> Optional[float]:
        """從錯誤中提取 retry_after"""
        error_str = str(error).lower()
        
        # 嘗試匹配 "retry after X seconds"
        import re
        match = re.search(r'retry\s*after\s*(\d+(?:\.\d+)?)', error_str)
        if match:
            return float(match.group(1))
        
        return None


# 便捷函數
def create_failover_router(
    max_retries: int = 3,
    rate_limit_retries: int = 5,
    enabled: bool = True
) -> AutoFailoverRouter:
    """創建 Failover Router"""
    config = FailoverConfig(
        enabled=enabled,
        max_retries=max_retries,
        rate_limit_retries=rate_limit_retries
    )
    return AutoFailoverRouter(config=config)
