"""
路由引擎 - Router Engine
實現 ReAct 設計模式和 L1-L4 錯誤處理
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import time
import logging

from .classifier import TaskClassifier, TaskType, ClassificationResult
from .registry import ModelRegistry, ModelInfo, Provider


class BudgetLevel(Enum):
    """預算等級"""
    LOW = "low"
    BALANCED = "balanced"
    HIGH = "high"


class ErrorLevel(Enum):
    """錯誤等級"""
    L1_INPUT = "L1_INPUT"       # 輸入錯誤
    L2_API = "L2_API"           # API 錯誤
    L3_EXECUTION = "L3_EXECUTION"  # 執行錯誤
    L4_SYSTEM = "L4_SYSTEM"     # 系統錯誤


@dataclass
class RouterConfig:
    """路由配置"""
    max_retries: int = 3
    retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5  # 熔斷閾值
    circuit_breaker_timeout: float = 60  # 熔斷恢復時間(秒)


@dataclass
class RouterResult:
    """路由結果"""
    model_id: str
    model_name: str
    provider: str
    reasoning: str
    estimated_cost: float
    estimated_latency: int
    confidence: float


class RouterError(Exception):
    """路由錯誤"""
    def __init__(self, level: ErrorLevel, message: str):
        self.level = level
        self.message = message
        super().__init__(f"[{level.value}] {message}")


class RouterEngine:
    """
    路由引擎 - 使用 ReAct 設計模式
    
    ReAct Pattern:
    - Reasoning: 分析任務和上下文
    - Action: 選擇最適合的模型
    - Observation: 觀察候選模型
    - Output: 返回最終推薦
    """
    
    def __init__(
        self, 
        classifier: Optional[TaskClassifier] = None,
        registry: Optional[ModelRegistry] = None,
        config: Optional[RouterConfig] = None
    ):
        self.classifier = classifier or TaskClassifier()
        self.registry = registry or ModelRegistry()
        self.config = config or RouterConfig()
        
        # 錯誤追蹤
        self._error_counts: Dict[str, int] = {}  # model_id -> error count
        self._circuit_breaker: Dict[str, float] = {}  # model_id -> break_until
        self._request_counts: Dict[str, int] = {}  # model_id -> request count
        
        # 日誌
        self.logger = logging.getLogger(__name__)
    
    def _is_circuit_broken(self, model_id: str) -> bool:
        """檢查是否熔斷"""
        if model_id not in self._circuit_breaker:
            return False
        return time.time() < self._circuit_breaker[model_id]
    
    def _trigger_circuit_break(self, model_id: str) -> None:
        """觸發熔斷"""
        self._circuit_breaker[model_id] = time.time() + self.config.circuit_breaker_timeout
        self.logger.warning(f"Circuit breaker triggered for {model_id}")
    
    def _record_error(self, model_id: str) -> None:
        """記錄錯誤"""
        self._error_counts[model_id] = self._error_counts.get(model_id, 0) + 1
        
        # 檢查是否觸發熔斷
        if self._error_counts[model_id] >= self.config.circuit_breaker_threshold:
            self._trigger_circuit_break(model_id)
    
    def _record_success(self, model_id: str) -> None:
        """記錄成功"""
        self._request_counts[model_id] = self._request_counts.get(model_id, 0) + 1
        # 成功後重置錯誤計數
        self._error_counts[model_id] = 0
    
    def _validate_input(self, task: str, budget: str) -> None:
        """
        L1 錯誤處理: 輸入驗證
        """
        if not task or not task.strip():
            raise RouterError(
                ErrorLevel.L1_INPUT,
                "任務描述不能為空"
            )
        
        valid_budgets = ["low", "balanced", "high", "auto"]
        if budget not in valid_budgets:
            raise RouterError(
                ErrorLevel.L1_INPUT,
                f"無效的預算選項: {budget}. 支援: {valid_budgets}"
            )
    
    def _select_best_model(
        self,
        task_type: TaskType,
        budget: BudgetLevel,
        preferred_model: Optional[str] = None
    ) -> ModelInfo:
        """
        ReAct Pattern: 推理 -> 行動 -> 觀察 -> 輸出
        """
        # 如果指定了特定模型
        if preferred_model:
            model = self.registry.get_model(preferred_model)
            if model:
                if not self._is_circuit_broken(preferred_model):
                    return model
                self.logger.warning(f"指定的模型 {preferred_model} 處於熔斷狀態")
            else:
                raise RouterError(
                    ErrorLevel.L1_INPUT,
                    f"未找到模型: {preferred_model}"
                )
        
        # Action: 獲取候選模型列表
        candidates = self.registry.get_models_for_task(task_type.value)
        
        # Observation: 過濾掉熔斷的模型
        candidates = [c for c in candidates if not self._is_circuit_broken(c.id)]
        
        if not candidates:
            # L4 錯誤處理: 所有模型都熔斷
            raise RouterError(
                ErrorLevel.L4_SYSTEM,
                f"所有適合 {task_type.value} 的模型都處於熔斷狀態"
            )
        
        # Reasoning: 根據預算和任務選擇最佳模型
        if budget == BudgetLevel.LOW:
            # 低成本優先
            candidates = sorted(
                candidates,
                key=lambda x: x.cost_per_1k_input + x.cost_per_1k_output
            )
        elif budget == BudgetLevel.HIGH:
            # 高性能優先 (上下文窗口 + 低延遲)
            candidates = sorted(
                candidates,
                key=lambda x: (-x.context_window, x.latency_ms)
            )
        else:  # balanced
            # 平衡選擇
            candidates = sorted(
                candidates,
                key=lambda x: (
                    x.cost_per_1k_input + x.cost_per_1k_output
                ) * (x.latency_ms / 1000)
            )
        
        # Output: 返回最佳模型
        return candidates[0]
    
    def route(
        self,
        task: str,
        budget: str = "auto",
        model: Optional[str] = None
    ) -> RouterResult:
        """
        主路由方法
        
        Args:
            task: 任務描述
            budget: 預算等級 (low/balanced/high/auto)
            model: 指定模型 ID
            
        Returns:
            RouterResult: 路由結果
        """
        # L1: 輸入驗證
        self._validate_input(task, budget)
        
        # ReAct Pattern
        # ============
        # Step 1: Reasoning - 分析任務
        classification = self.classifier.classify(task)
        task_type = classification.task_type
        confidence = classification.confidence
        
        reasoning_parts = [
            f"[Reasoning] 任務分類: {task_type.value}",
            f"[Reasoning] 置信度: {confidence}",
        ]
        
        # Step 2: Action - 選擇模型
        # 如果預算是 auto，根據任務類型自動選擇
        if budget == "auto":
            budget = self._infer_budget(task_type)
        
        try:
            selected_model = self._select_best_model(
                task_type,
                BudgetLevel(budget),
                preferred_model=model
            )
        except RouterError as e:
            if e.level == ErrorLevel.L4_SYSTEM:
                # L4: 嘗試降級處理
                return self._fallback_route(task, budget, e.message)
            raise
        
        reasoning_parts.extend([
            f"[Action] 選擇模型: {selected_model.name}",
            f"[Action] 提供商: {selected_model.provider.value}",
        ])
        
        # Step 3: Observation - 觀察候選模型
        reasoning_parts.append(
            f"[Observation] 預估成本: ${selected_model.cost_per_1k_input:.4f}/input, "
            f"${selected_model.cost_per_1k_output:.4f}/output"
        )
        reasoning_parts.append(
            f"[Observation] 預估延遲: {selected_model.latency_ms}ms"
        )
        
        # Step 4: Output
        return RouterResult(
            model_id=selected_model.id,
            model_name=selected_model.name,
            provider=self.registry.get_provider_name(selected_model.provider),
            reasoning="\n".join(reasoning_parts),
            estimated_cost=selected_model.cost_per_1k_input + selected_model.cost_per_1k_output,
            estimated_latency=selected_model.latency_ms,
            confidence=confidence
        )
    
    def _infer_budget(self, task_type: TaskType) -> str:
        """根據任務類型推斷預算"""
        # 代碼相關任務默認使用 balanced
        if task_type in [TaskType.CODE_GENERATION, TaskType.CODE_REVIEW]:
            return "balanced"
        # 簡單對話使用 low
        if task_type == TaskType.CONVERSATION:
            return "low"
        # 其他使用 balanced
        return "balanced"
    
    def _fallback_route(
        self, 
        task: str, 
        budget: str, 
        error_msg: str
    ) -> RouterResult:
        """L3/L4 錯誤處理: 降級處理"""
        self.logger.warning(f"Fallback route triggered: {error_msg}")
        
        # 嘗試獲取任何可用的模型
        all_models = self.registry.list_models()
        available = [m for m in all_models if not self._is_circuit_broken(m.id)]
        
        if not available:
            raise RouterError(
                ErrorLevel.L4_SYSTEM,
                "無法找到可用的模型"
            )
        
        # 選擇最便宜的模型
        fallback_model = min(
            available,
            key=lambda x: x.cost_per_1k_input + x.cost_per_1k_output
        )
        
        return RouterResult(
            model_id=fallback_model.id,
            model_name=fallback_model.name,
            provider=self.registry.get_provider_name(fallback_model.provider),
            reasoning=f"[Fallback] {error_msg}\n使用備用模型: {fallback_model.name}",
            estimated_cost=fallback_model.cost_per_1k_input + fallback_model.cost_per_1k_output,
            estimated_latency=fallback_model.latency_ms,
            confidence=0.0
        )
    
    def get_status(self) -> Dict[str, Any]:
        """獲取路由引擎狀態"""
        return {
            "error_counts": self._error_counts.copy(),
            "circuit_breakers": {
                k: v for k, v in self._circuit_breaker.items() 
                if v > time.time()
            },
            "request_counts": self._request_counts.copy(),
        }
    
    def reset_circuit_breaker(self, model_id: Optional[str] = None) -> None:
        """重置熔斷"""
        if model_id:
            self._circuit_breaker.pop(model_id, None)
            self._error_counts.pop(model_id, None)
        else:
            self._circuit_breaker.clear()
            self._error_counts.clear()


class TaskAwareRouter:
    """
    任務感知定價路由器
    
    根據任務複雜度和預算自動選擇最佳模型
    支援 budget 參數 (low/medium/high) 自動優化成本
    """
    
    # 任務複雜度評估
    TASK_COMPLEXITY = {
        TaskType.CODE_GENERATION: "high",
        TaskType.CODE_REVIEW: "high",
        TaskType.DATA_ANALYSIS: "high",
        TaskType.TEXT_SUMMARIZATION: "medium",
        TaskType.TRANSLATION: "medium",
        TaskType.CONVERSATION: "low",
        TaskType.IMAGE_UNDERSTANDING: "medium",
    }
    
    # 預算對應的模型選擇策略
    BUDGET_STRATEGY = {
        "low": {
            "max_cost": 0.001,  # 每 1K tokens 最大成本
            "prefer": ["minimax", "gemini-flash", "haiku"],
        },
        "medium": {
            "max_cost": 0.01,
            "prefer": ["gpt-4o-mini", "claude-haiku", "gemini-flash"],
        },
        "high": {
            "max_cost": 0.1,
            "prefer": ["gpt-4o", "claude-opus", "claude-sonnet", "gemini-pro"],
        }
    }
    
    def __init__(
        self,
        classifier: Optional[TaskClassifier] = None,
        registry: Optional[ModelRegistry] = None,
        config: Optional[RouterConfig] = None
    ):
        self.classifier = classifier or TaskClassifier()
        self.registry = registry or ModelRegistry()
        self.config = config or RouterConfig()
        self.logger = logging.getLogger(__name__)
    
    def _evaluate_task_complexity(self, task: str) -> str:
        """評估任務複雜度"""
        # 關鍵詞分析
        complex_keywords = [
            "分析", "評估", "設計", "優化", "重構", "debug",
            "review", "analyze", "design", "optimize", "refactor",
            "複雜", "困難", "深度", "完整", "全面"
        ]
        
        simple_keywords = [
            "翻譯", "摘要", "簡單", "基礎",
            "translate", "summarize", "simple", "basic"
        ]
        
        task_lower = task.lower()
        
        complex_count = sum(1 for kw in complex_keywords if kw in task_lower)
        simple_count = sum(1 for kw in simple_keywords if kw in task_lower)
        
        if complex_count > simple_count:
            return "high"
        elif simple_count > complex_count:
            return "low"
        else:
            return "medium"
    
    def _select_cheap_model(
        self,
        task_type: TaskType,
        candidates: List[ModelInfo]
    ) -> Optional[ModelInfo]:
        """選擇低價模型"""
        if not candidates:
            return None
        
        # 優先選擇專用於該任務的低價模型
        strategy = self.BUDGET_STRATEGY["low"]
        
        # 按成本排序
        sorted_by_cost = sorted(
            candidates,
            key=lambda x: x.cost_per_1k_input + x.cost_per_1k_output
        )
        
        # 嘗試找到符合預算的模型
        for model in sorted_by_cost:
            cost = model.cost_per_1k_input + model.cost_per_1k_output
            if cost <= strategy["max_cost"]:
                return model
        
        # 如果沒有符合預算的，返回最便宜的
        return sorted_by_cost[0] if sorted_by_cost else None
    
    def _select_best_model(
        self,
        task_type: TaskType,
        candidates: List[ModelInfo]
    ) -> Optional[ModelInfo]:
        """選擇高性能模型"""
        if not candidates:
            return None
        
        strategy = self.BUDGET_STRATEGY["high"]
        
        # 按性能排序: 上下文窗口大、延遲低、能力強
        sorted_by_performance = sorted(
            candidates,
            key=lambda x: (-x.context_window, x.latency_ms)
        )
        
        # 優先選擇符合關鍵詞的模型
        for model in sorted_by_performance:
            for keyword in strategy["prefer"]:
                if keyword in model.id.lower():
                    return model
        
        return sorted_by_performance[0] if sorted_by_performance else None
    
    def _select_balanced_model(
        self,
        task_type: TaskType,
        candidates: List[ModelInfo]
    ) -> Optional[ModelInfo]:
        """選擇平衡模型"""
        if not candidates:
            return None
        
        # 計算性價比
        def calc_value(model: ModelInfo) -> float:
            cost = model.cost_per_1k_input + model.cost_per_1k_output
            if cost == 0:
                return float('inf')
            # 性價比 = 上下文 / (成本 * 延遲)
            return model.context_window / (cost * model.latency_ms)
        
        sorted_by_value = sorted(
            candidates,
            key=calc_value,
            reverse=True
        )
        
        return sorted_by_value[0] if sorted_by_value else None
    
    def route_by_budget(
        self,
        task: str,
        budget: str,
        task_type: Optional[TaskType] = None
    ) -> RouterResult:
        """
        根據預算路由
        
        Args:
            task: 任務描述
            budget: 預算等級 (low/medium/high)
            task_type: 任務類型 (可選，如果未提供會自動分類)
            
        Returns:
            RouterResult: 路由結果
        """
        # 如果未提供任務類型，自動分類
        if task_type is None:
            classification = self.classifier.classify(task)
            task_type = classification.task_type
            confidence = classification.confidence
        else:
            confidence = 0.8
        
        # 獲取候選模型
        candidates = self.registry.get_models_for_task(task_type.value)
        
        if not candidates:
            raise RouterError(
                ErrorLevel.L4_SYSTEM,
                f"無法找到適合 {task_type.value} 的模型"
            )
        
        # 根據預算選擇模型
        if budget == "low":
            selected = self._select_cheap_model(task_type, candidates)
        elif budget == "high":
            selected = self._select_best_model(task_type, candidates)
        else:  # medium/balanced
            selected = self._select_balanced_model(task_type, candidates)
        
        if not selected:
            raise RouterError(
                ErrorLevel.L4_SYSTEM,
                "無法選擇合適的模型"
            )
        
        # 構建推理過程
        complexity = self._evaluate_task_complexity(task)
        reasoning_parts = [
            f"[TaskAware] 任務複雜度評估: {complexity}",
            f"[TaskAware] 任務類型: {task_type.value}",
            f"[TaskAware] 預算等級: {budget}",
            f"[TaskAware] 候選模型數: {len(candidates)}",
            f"[TaskAware] 選擇模型: {selected.name}",
            f"[TaskAware] 預估成本: ${selected.cost_per_1k_input:.4f}/input, "
            f"${selected.cost_per_1k_output:.4f}/output",
        ]
        
        return RouterResult(
            model_id=selected.id,
            model_name=selected.name,
            provider=self.registry.get_provider_name(selected.provider),
            reasoning="\n".join(reasoning_parts),
            estimated_cost=selected.cost_per_1k_input + selected.cost_per_1k_output,
            estimated_latency=selected.latency_ms,
            confidence=confidence
        )
    
    def estimate_cost(
        self,
        task: str,
        budget: str,
        estimated_input_tokens: int = 1000,
        estimated_output_tokens: int = 500
    ) -> Dict[str, float]:
        """估算成本"""
        result = self.route_by_budget(task, budget)
        
        input_cost = (estimated_input_tokens / 1000) * (
            self.registry.get_model(result.model_id).cost_per_1k_input
            if self.registry.get_model(result.model_id) else result.estimated_cost
        )
        output_cost = (estimated_output_tokens / 1000) * (
            self.registry.get_model(result.model_id).cost_per_1k_output
            if self.registry.get_model(result.model_id) else result.estimated_cost
        )
        
        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
            "model_id": result.model_id,
            "model_name": result.model_name
        }
