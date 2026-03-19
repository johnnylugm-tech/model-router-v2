"""
Config Module - 模型分層配置
支援 YAML 配置文件、模型層級定義和任務覆寫
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class LayerConfig:
    """單層配置"""
    model: str = "gpt-4o-mini"
    budget: str = "balanced"


@dataclass
class RoutingConfig:
    """路由配置"""
    defaults: Dict[str, str] = field(default_factory=lambda: {
        "primary": "gpt-4o-mini",
        "fallback": ["gpt-4o", "gemini-1.5-flash"]
    })
    heartbeat: LayerConfig = field(default_factory=LayerConfig)
    subagent: LayerConfig = field(default_factory=LayerConfig)
    task_overrides: Dict[str, str] = field(default_factory=dict)


@dataclass
class FailoverConfig:
    """Failover 配置"""
    enabled: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_retries: int = 5
    rate_limit_backoff: float = 2.0


@dataclass
class Config:
    """完整配置"""
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    failover: FailoverConfig = field(default_factory=FailoverConfig)


class ConfigLoader:
    """配置載入器"""
    
    DEFAULT_CONFIG = {
        "routing": {
            "defaults": {
                "primary": "gpt-4o-mini",
                "fallback": ["gpt-4o", "gemini-1.5-flash", "claude-3-5-sonnet"]
            },
            "heartbeat": {
                "model": "gemini-1.5-flash",
                "budget": "low"
            },
            "subagent": {
                "model": "claude-3-haiku",
                "budget": "low"
            },
            "task_overrides": {
                "CODE_REVIEW": "claude-3-5-sonnet",
                "CODE_GENERATION": "claude-3-5-sonnet",
                "TRANSLATION": "minimax-abab6.5s-chat",
                "CONVERSATION": "gpt-4o-mini",
                "DATA_ANALYSIS": "gpt-4o",
                "IMAGE_UNDERSTANDING": "gpt-4o",
                "TEXT_SUMMARIZATION": "gemini-1.5-flash"
            }
        },
        "failover": {
            "enabled": True,
            "max_retries": 3,
            "retry_delay": 1.0,
            "rate_limit_retries": 5,
            "rate_limit_backoff": 2.0
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[Config] = None
    
    def _get_default_config_path(self) -> str:
        """獲取默認配置路徑"""
        # 優先使用專案目錄下的 config.yaml
        project_dir = Path(__file__).parent.parent
        config_file = project_dir / "config.yaml"
        
        if config_file.exists():
            return str(config_file)
        
        # 其次檢查當前目錄
        if Path("config.yaml").exists():
            return "config.yaml"
        
        # 使用家目錄
        home_config = Path.home() / ".model-router" / "config.yaml"
        if home_config.exists():
            return str(home_config)
        
        return None
    
    def load(self) -> Config:
        """載入配置"""
        if self._config:
            return self._config
        
        if not self.config_path or not Path(self.config_path).exists():
            # 使用默認配置
            self._config = self._parse_dict(self.DEFAULT_CONFIG)
            return self._config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                data = self.DEFAULT_CONFIG
            
            # 合併默認配置
            data = self._merge_config(data)
            self._config = self._parse_dict(data)
            return self._config
            
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
            self._config = self._parse_dict(self.DEFAULT_CONFIG)
            return self._config
    
    def _merge_config(self, data: dict) -> dict:
        """合併配置"""
        result = self.DEFAULT_CONFIG.copy()
        
        if "routing" in data:
            result["routing"] = self._deep_merge(result["routing"], data["routing"])
        
        if "failover" in data:
            result["failover"] = self._deep_merge(result["failover"], data["failover"])
        
        return result
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """深度合併字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _parse_dict(self, data: dict) -> Config:
        """解析配置字典"""
        routing_data = data.get("routing", {})
        
        defaults = routing_data.get("defaults", {})
        routing_config = RoutingConfig(
            defaults=defaults,
            heartbeat=LayerConfig(**routing_data.get("heartbeat", {})),
            subagent=LayerConfig(**routing_data.get("subagent", {})),
            task_overrides=routing_data.get("task_overrides", {})
        )
        
        failover_data = data.get("failover", {})
        failover_config = FailoverConfig(**failover_data)
        
        return Config(
            routing=routing_config,
            failover=failover_config
        )
    
    def get_primary_model(self, task_type: Optional[str] = None) -> str:
        """獲取主要模型"""
        config = self.load()
        
        # 檢查任務覆寫
        if task_type and task_type in config.routing.task_overrides:
            return config.routing.task_overrides[task_type]
        
        return config.routing.defaults.get("primary", "gpt-4o-mini")
    
    def get_fallback_models(self) -> List[str]:
        """獲取 Fallback 模型列表"""
        config = self.load()
        fallback = config.routing.defaults.get("fallback", [])
        if isinstance(fallback, str):
            fallback = [fallback]
        return fallback
    
    def get_heartbeat_config(self) -> LayerConfig:
        """獲取 Heartbeat 配置"""
        return self.load().routing.heartbeat
    
    def get_subagent_config(self) -> LayerConfig:
        """獲取 Subagent 配置"""
        return self.load().routing.subagent
    
    def get_task_override(self, task_type: str) -> Optional[str]:
        """獲取任務覆寫"""
        return self.load().routing.task_overrides.get(task_type)
    
    def is_failover_enabled(self) -> bool:
        """是否啟用 Failover"""
        return self.load().failover.enabled
    
    def get_failover_config(self) -> FailoverConfig:
        """獲取 Failover 配置"""
        return self.load().failover
    
    def reload(self) -> Config:
        """重新載入配置"""
        self._config = None
        return self.load()
    
    def to_yaml(self) -> str:
        """導出為 YAML"""
        config = self.load()
        
        data = {
            "routing": {
                "defaults": config.routing.defaults,
                "heartbeat": {
                    "model": config.routing.heartbeat.model,
                    "budget": config.routing.heartbeat.budget
                },
                "subagent": {
                    "model": config.routing.subagent.model,
                    "budget": config.routing.subagent.budget
                },
                "task_overrides": config.routing.task_overrides
            },
            "failover": {
                "enabled": config.failover.enabled,
                "max_retries": config.failover.max_retries,
                "retry_delay": config.failover.retry_delay,
                "rate_limit_retries": config.failover.rate_limit_retries,
                "rate_limit_backoff": config.failover.rate_limit_backoff
            }
        }
        
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)


# 全局配置實例
_default_loader: Optional[ConfigLoader] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """獲取配置實例"""
    global _default_loader
    if _default_loader is None:
        _default_loader = ConfigLoader(config_path)
    return _default_loader.load()


def reload_config() -> Config:
    """重新載入配置"""
    global _default_loader
    if _default_loader:
        return _default_loader.reload()
    return get_config()
