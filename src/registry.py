"""
模型註冊表 - Model Registry
支援 OpenAI, Anthropic, Google, MiniMax
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional


class Provider(Enum):
    """模型提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MINIMAX = "minimax"
    DEEPSEEK = "deepseek"


@dataclass
class ModelInfo:
    """模型資訊"""
    id: str
    name: str
    provider: Provider
    cost_per_1k_input: float      # $ per 1K input tokens
    cost_per_1k_output: float      # $ per 1K output tokens
    latency_ms: int                # 預估延遲 (毫秒)
    context_window: int            # 上下文視窗大小 (tokens)
    strengths: List[str]           # 擅長領域
    weaknesses: List[str]          # 劣勢
    best_for: List[str]            # 最佳用途


class ModelRegistry:
    """模型註冊表 - 管理和查詢模型資訊"""
    
    # 預設模型註冊表
    MODELS: Dict[str, ModelInfo] = {
        # OpenAI Models
        "gpt-4o": ModelInfo(
            id="gpt-4o",
            name="GPT-4o",
            provider=Provider.OPENAI,
            cost_per_1k_input=0.005,
            cost_per_1k_output=0.015,
            latency_ms=2000,
            context_window=128000,
            strengths=["代碼生成", "複雜推理", "多模態", "創意寫作"],
            weaknesses=["成本較高", "有時過度謹慎"],
            best_for=["CODE_GENERATION", "CODE_REVIEW", "CONVERSATION"]
        ),
        "gpt-4o-mini": ModelInfo(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            provider=Provider.OPENAI,
            cost_per_1k_input=0.00015,
            cost_per_1k_output=0.0006,
            latency_ms=800,
            context_window=128000,
            strengths=["低成本", "快速響應", "高效率"],
            weaknesses=["複雜推理較弱"],
            best_for=["CONVERSATION", "TEXT_SUMMARIZATION", "TRANSLATION"]
        ),
        "gpt-4-turbo": ModelInfo(
            id="gpt-4-turbo",
            name="GPT-4 Turbo",
            provider=Provider.OPENAI,
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.03,
            latency_ms=2500,
            context_window=128000,
            strengths=["代碼", "推理", "上下文理解"],
            weaknesses=["成本高"],
            best_for=["CODE_GENERATION", "CODE_REVIEW", "DATA_ANALYSIS"]
        ),
        "gpt-3.5-turbo": ModelInfo(
            id="gpt-3.5-turbo",
            name="GPT-3.5 Turbo",
            provider=Provider.OPENAI,
            cost_per_1k_input=0.0005,
            cost_per_1k_output=0.0015,
            latency_ms=600,
            context_window=16385,
            strengths=["快速", "低成本", "日常對話"],
            weaknesses=["複雜推理", "長上下文"],
            best_for=["CONVERSATION", "TRANSLATION", "TEXT_SUMMARIZATION"]
        ),
        
        # Anthropic Models
        "claude-3-5-sonnet": ModelInfo(
            id="claude-3-5-sonnet",
            name="Claude 3.5 Sonnet",
            provider=Provider.ANTHROPIC,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            latency_ms=1800,
            context_window=200000,
            strengths=["代碼審查", "指令遵循", "安全合規", "長文本"],
            weaknesses=["成本偏高"],
            best_for=["CODE_REVIEW", "CODE_GENERATION", "TEXT_SUMMARIZATION"]
        ),
        "claude-3-opus": ModelInfo(
            id="claude-3-opus",
            name="Claude 3 Opus",
            provider=Provider.ANTHROPIC,
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075,
            latency_ms=3000,
            context_window=200000,
            strengths=["複雜推理", "深度分析", "創意寫作"],
            weaknesses=["成本很高", "延遲較高"],
            best_for=["DATA_ANALYSIS", "CONVERSATION", "CODE_GENERATION"]
        ),
        "claude-3-haiku": ModelInfo(
            id="claude-3-haiku",
            name="Claude 3 Haiku",
            provider=Provider.ANTHROPIC,
            cost_per_1k_input=0.00025,
            cost_per_1k_output=0.00125,
            latency_ms=500,
            context_window=200000,
            strengths=["快速", "低成本", "日常任務"],
            weaknesses=["深度推理較弱"],
            best_for=["CONVERSATION", "TRANSLATION", "TEXT_SUMMARIZATION"]
        ),
        
        # Google Models
        "gemini-1.5-pro": ModelInfo(
            id="gemini-1.5-pro",
            name="Gemini 1.5 Pro",
            provider=Provider.GOOGLE,
            cost_per_1k_input=0.00125,
            cost_per_1k_output=0.005,
            latency_ms=1500,
            context_window=2000000,
            strengths=["超長上下文", "多模態", "價格合理"],
            weaknesses=["某些任務不穩定"],
            best_for=["DATA_ANALYSIS", "IMAGE_UNDERSTANDING", "TEXT_SUMMARIZATION"]
        ),
        "gemini-1.5-flash": ModelInfo(
            id="gemini-1.5-flash",
            name="Gemini 1.5 Flash",
            provider=Provider.GOOGLE,
            cost_per_1k_input=0.000075,
            cost_per_1k_output=0.0003,
            latency_ms=400,
            context_window=1000000,
            strengths=["超快速", "極低成本", "長上下文"],
            weaknesses=["複雜任務較弱"],
            best_for=["CONVERSATION", "TRANSLATION", "IMAGE_UNDERSTANDING"]
        ),
        
        # MiniMax Models
        "minimax-abab6.5s-chat": ModelInfo(
            id="minimax-abab6.5s-chat",
            name="MiniMax Abab 6.5s",
            provider=Provider.MINIMAX,
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0001,
            latency_ms=600,
            context_window=245000,
            strengths=["中文優化", "極低成本", "快速響應"],
            weaknesses=["英文能力較弱"],
            best_for=["CONVERSATION", "TRANSLATION", "TEXT_SUMMARIZATION"]
        ),
        "minimax-abab6.5g-chat": ModelInfo(
            id="minimax-abab6.5g-chat",
            name="MiniMax Abab 6.5g",
            provider=Provider.MINIMAX,
            cost_per_1k_input=0.0002,
            cost_per_1k_output=0.0002,
            latency_ms=800,
            context_window=245000,
            strengths=["中文強項", "多語言", "性價比高"],
            weaknesses=["特定領域知識有限"],
            best_for=["CONVERSATION", "TRANSLATION", "DATA_ANALYSIS"]
        ),
        
        # DeepSeek Models
        "deepseek-v4": ModelInfo(
            id="deepseek-v4",
            name="DeepSeek V4",
            provider=Provider.DEEPSEEK,
            cost_per_1k_input=0.5,
            cost_per_1k_output=2.0,
            latency_ms=2000,
            context_window=64000,
            strengths=["代碼生成", "推理", "數學"],
            weaknesses=["品牌認知度較低"],
            best_for=["CODE_GENERATION", "CODE_REVIEW", "DATA_ANALYSIS"]
        ),
        "deepseek-v3": ModelInfo(
            id="deepseek-v3",
            name="DeepSeek V3",
            provider=Provider.DEEPSEEK,
            cost_per_1k_input=0.27,
            cost_per_1k_output=1.1,
            latency_ms=1000,
            context_window=64000,
            strengths=["代碼生成", "快速響應"],
            weaknesses=["品牌認知度較低"],
            best_for=["CODE_GENERATION", "CONVERSATION", "TRANSLATION"]
        ),
    }
    
    # 任務類型到推薦模型
    TASK_MODEL_MAP: Dict[str, List[str]] = {
        "CODE_GENERATION": [
            "claude-3-5-sonnet", "gpt-4o", "gpt-4-turbo", "claude-3-opus",
            "deepseek-v4", "deepseek-v3"
        ],
        "CODE_REVIEW": [
            "claude-3-5-sonnet", "gpt-4o", "claude-3-opus", "gpt-4-turbo",
            "deepseek-v4"
        ],
        "TEXT_SUMMARIZATION": [
            "gemini-1.5-flash", "claude-3-haiku", "gpt-3.5-turbo", 
            "minimax-abab6.5s-chat", "gemini-1.5-pro"
        ],
        "TRANSLATION": [
            "gpt-4o-mini", "claude-3-haiku", "gemini-1.5-flash",
            "minimax-abab6.5s-chat", "gpt-3.5-turbo", "deepseek-v3"
        ],
        "CONVERSATION": [
            "gpt-4o-mini", "claude-3-haiku", "gemini-1.5-flash",
            "minimax-abab6.5s-chat", "gpt-3.5-turbo", "deepseek-v3"
        ],
        "IMAGE_UNDERSTANDING": [
            "gpt-4o", "gemini-1.5-pro", "gemini-1.5-flash"
        ],
        "DATA_ANALYSIS": [
            "gpt-4o", "claude-3-opus", "gemini-1.5-pro", 
            "minimax-abab6.5g-chat", "gpt-4-turbo", "deepseek-v4"
        ],
    }
    
    def __init__(self):
        self._models = self.MODELS.copy()
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """獲取指定模型資訊"""
        return self._models.get(model_id)
    
    def list_models(self, provider: Optional[Provider] = None) -> List[ModelInfo]:
        """列出所有模型或指定提供商的模型"""
        if provider:
            return [m for m in self._models.values() if m.provider == provider]
        return list(self._models.values())
    
    def get_models_for_task(self, task_type: str) -> List[ModelInfo]:
        """獲取適合特定任務類型的模型列表"""
        model_ids = self.TASK_MODEL_MAP.get(task_type, [])
        return [self._models[mid] for mid in model_ids if mid in self._models]
    
    def get_models_by_budget(self, budget: str) -> List[ModelInfo]:
        """根據預算獲取模型"""
        if budget == "low":
            # 低成本模型
            return sorted(
                [m for m in self._models.values()],
                key=lambda x: x.cost_per_1k_input + x.cost_per_1k_output
            )[:5]
        elif budget == "high":
            # 高性能模型
            return sorted(
                [m for m in self._models.values()],
                key=lambda x: -x.context_window
            )[:5]
        else:  # balanced
            # 平衡模型
            return sorted(
                [m for m in self._models.values()],
                key=lambda x: (x.cost_per_1k_input + x.cost_per_1k_output) * x.latency_ms / 1000
            )[:5]
    
    def register_model(self, model: ModelInfo) -> None:
        """註冊新模型"""
        self._models[model.id] = model
    
    def get_provider_name(self, provider: Enum) -> str:
        """獲取提供商顯示名稱"""
        names = {
            Provider.OPENAI: "OpenAI",
            Provider.ANTHROPIC: "Anthropic",
            Provider.GOOGLE: "Google",
            Provider.MINIMAX: "MiniMax",
            Provider.DEEPSEEK: "DeepSeek",
        }
        return names.get(provider, str(provider))
