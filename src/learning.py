"""
動態路由學習 - Dynamic Routing Learning
記錄任務歷史、學習用戶偏好、基於歷史優化路由決策
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import json
import os
import logging


@dataclass
class TaskHistory:
    """任務歷史記錄"""
    timestamp: str
    task_description: str
    task_type: str
    model_id: str
    model_name: str
    confidence: float
    cost: float
    latency_ms: int
    success: bool
    user_rating: Optional[int] = None  # 用戶評分 1-5


@dataclass
class UserPreference:
    """用戶偏好"""
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    budget_level: str = "auto"
    max_latency_ms: Optional[int] = None
    preferred_task_models: Dict[str, str] = field(default_factory=dict)


@dataclass
class LearningStats:
    """學習統計"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_confidence: float = 0.0
    avg_cost: float = 0.0
    avg_latency: float = 0.0
    provider_preference: Dict[str, int] = field(default_factory=dict)
    task_model_mapping: Dict[str, str] = field(default_factory=dict)


class RoutingLearner:
    """路由學習器"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化路由學習器
        
        Args:
            data_dir: 數據存儲目錄
        """
        self.data_dir = data_dir or os.path.expanduser("~/.model-router")
        self.history_file = os.path.join(self.data_dir, "task_history.json")
        self.preferences_file = os.path.join(self.data_dir, "user_preferences.json")
        
        # 內存存儲
        self._history: List[TaskHistory] = []
        self._preferences = UserPreference()
        
        # 加載數據
        self._load_history()
        self._load_preferences()
        
        # 日誌
        self.logger = logging.getLogger(__name__)
    
    def _load_history(self) -> None:
        """加載歷史記錄"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self._history = [
                        TaskHistory(**h) for h in data.get('history', [])
                    ]
            except Exception as e:
                self.logger.warning(f"加載歷史記錄失敗: {e}")
                self._history = []
    
    def _save_history(self) -> None:
        """保存歷史記錄"""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.history_file, 'w') as f:
            json.dump({
                'history': [
                    {
                        'timestamp': h.timestamp,
                        'task_description': h.task_description,
                        'task_type': h.task_type,
                        'model_id': h.model_id,
                        'model_name': h.model_name,
                        'confidence': h.confidence,
                        'cost': h.cost,
                        'latency_ms': h.latency_ms,
                        'success': h.success,
                        'user_rating': h.user_rating,
                    }
                    for h in self._history
                ]
            }, f, indent=2)
    
    def _load_preferences(self) -> None:
        """加載用戶偏好"""
        if os.path.exists(self.preferences_file):
            try:
                with open(self.preferences_file, 'r') as f:
                    data = json.load(f)
                    self._preferences = UserPreference(**data)
            except Exception as e:
                self.logger.warning(f"加載用戶偏好失敗: {e}")
                self._preferences = UserPreference()
    
    def _save_preferences(self) -> None:
        """保存用戶偏好"""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.preferences_file, 'w') as f:
            json.dump({
                'preferred_provider': self._preferences.preferred_provider,
                'preferred_model': self._preferences.preferred_model,
                'budget_level': self._preferences.budget_level,
                'max_latency_ms': self._preferences.max_latency_ms,
                'preferred_task_models': self._preferences.preferred_task_models,
            }, f, indent=2)
    
    def record_task(
        self,
        task_description: str,
        task_type: str,
        model_id: str,
        model_name: str,
        confidence: float,
        cost: float,
        latency_ms: int,
        success: bool
    ) -> None:
        """記錄任務執行"""
        history = TaskHistory(
            timestamp=datetime.now().isoformat(),
            task_description=task_description,
            task_type=task_type,
            model_id=model_id,
            model_name=model_name,
            confidence=confidence,
            cost=cost,
            latency_ms=latency_ms,
            success=success
        )
        
        self._history.append(history)
        self._save_history()
        
        # 學習：用戶使用的模型
        if success:
            self._learn_task_model_preference(task_type, model_id)
    
    def rate_task(
        self,
        task_description: str,
        rating: int
    ) -> None:
        """
        對任務進行評分
        
        Args:
            task_description: 任務描述
            rating: 評分 (1-5)
        """
        rating = max(1, min(5, rating))
        
        # 找到最近的匹配任務
        for history in reversed(self._history):
            if history.task_description == task_description:
                history.user_rating = rating
                self._save_history()
                
                # 學習：高分意味著用戶偏好該模型
                if rating >= 4:
                    self._learn_task_model_preference(
                        history.task_type, 
                        history.model_id
                    )
                break
    
    def _learn_task_model_preference(
        self, 
        task_type: str, 
        model_id: str
    ) -> None:
        """學習任務類型到模型的偏好"""
        # 記錄使用次數
        task_model_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        
        for h in self._history:
            if h.task_type == task_type and h.success:
                task_model_counts[(h.task_type, h.model_id)] += 1
        
        # 找出最常用的模型
        if task_model_counts:
            best_model = max(
                task_model_counts.items(),
                key=lambda x: x[1]
            )[0][1]
            
            self._preferences.preferred_task_models[task_type] = best_model
            self._save_preferences()
    
    def get_recommended_model(
        self,
        task_type: str,
        fallback_model: str = None
    ) -> Optional[str]:
        """
        根據歷史學習獲取推薦模型
        
        Args:
            task_type: 任務類型
            fallback_model: 備用模型
            
        Returns:
            Optional[str]: 推薦的模型 ID
        """
        # 檢查用戶偏好的任務模型
        if task_type in self._preferences.preferred_task_models:
            return self._preferences.preferred_task_models[task_type]
        
        # 沒有偏好，從歷史中學習
        task_models: Dict[str, int] = defaultdict(int)
        
        for h in self._history:
            if h.task_type == task_type and h.success:
                # 加權計算：成功+高分權重更高
                weight = 1
                if h.user_rating:
                    weight = h.user_rating
                task_models[h.model_id] += weight
        
        if task_models:
            return max(task_models.items(), key=lambda x: x[1])[0]
        
        return fallback_model
    
    def set_preference(
        self,
        provider: str = None,
        model: str = None,
        budget_level: str = None,
        max_latency_ms: int = None
    ) -> None:
        """設置用戶偏好"""
        if provider is not None:
            self._preferences.preferred_provider = provider
        if model is not None:
            self._preferences.preferred_model = model
        if budget_level is not None:
            self._preferences.budget_level = budget_level
        if max_latency_ms is not None:
            self._preferences.max_latency_ms = max_latency_ms
        
        self._save_preferences()
    
    def get_preferences(self) -> UserPreference:
        """獲取當前用戶偏好"""
        return self._preferences
    
    def get_stats(self) -> LearningStats:
        """獲取學習統計"""
        stats = LearningStats()
        
        if not self._history:
            return stats
        
        stats.total_tasks = len(self._history)
        
        successful = [h for h in self._history if h.success]
        stats.successful_tasks = len(successful)
        stats.failed_tasks = stats.total_tasks - stats.successful_tasks
        
        if successful:
            stats.avg_confidence = sum(h.confidence for h in successful) / len(successful)
            stats.avg_cost = sum(h.cost for h in successful) / len(successful)
            stats.avg_latency = sum(h.latency_ms for h in successful) / len(successful)
        
        # 提供商偏好
        for h in self._history:
            provider = h.model_id.split('-')[0]  # 簡單提取提供商
            stats.provider_preference[provider] = \
                stats.provider_preference.get(provider, 0) + 1
        
        # 任務-模型映射
        stats.task_model_mapping = dict(self._preferences.preferred_task_models)
        
        return stats
    
    def get_status_summary(self) -> str:
        """獲取狀態摘要"""
        stats = self.get_stats()
        prefs = self._preferences
        
        lines = [
            "=" * 50,
            "🧠 路由學習狀態",
            "=" * 50,
            f"總任務數: {stats.total_tasks}",
            f"成功: {stats.successful_tasks} | 失敗: {stats.failed_tasks}",
            "-" * 50,
            "📊 平均指標:",
            f"  置信度: {stats.avg_confidence:.1%}",
            f"  成本: ${stats.avg_cost:.4f}",
            f"  延遲: {stats.avg_latency:.0f}ms",
            "-" * 50,
            "⚙️ 用戶偏好:",
            f"  偏好提供商: {prefs.preferred_provider or '未設置'}",
            f"  偏好模型: {prefs.preferred_model or '未設置'}",
            f"  預算等級: {prefs.budget_level}",
            f"  最大延遲: {prefs.max_latency_ms or '無限制'}ms",
        ]
        
        if stats.task_model_mapping:
            lines.extend([
                "-" * 50,
                "🎯 學習到的任務-模型偏好:",
            ])
            for task, model in stats.task_model_mapping.items():
                lines.append(f"  • {task} → {model}")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def clear_history(self) -> None:
        """清除歷史記錄"""
        self._history.clear()
        if os.path.exists(self.history_file):
            os.remove(self.history_file)
    
    def reset_preferences(self) -> None:
        """重置偏好設置"""
        self._preferences = UserPreference()
        if os.path.exists(self.preferences_file):
            os.remove(self.preferences_file)


# 便捷函數
def get_learner() -> RoutingLearner:
    """獲取學習器實例"""
    return RoutingLearner()
