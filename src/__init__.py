"""
Model Router

智慧模型路由系統 - 根據任務類型自動選擇最適合的 AI 模型

## 功能特性

- **任務分類器**: 自動識別 7 種任務類型
- **模型註冊表**: 支援 OpenAI, Anthropic, Google, MiniMax
- **智能路由**: 基於成本、延遲、任務特性選擇最佳模型
- **錯誤處理**: L1-L4 四級錯誤處理機制
- **趨勢分析**: 追蹤任務分佈、模型使用、成本趨勢
- **API 整合**: 統一客戶端支援多種提供商
- **動態學習**: 基於歷史優化路由決策
- **迴歸檢測**: 監控模型品質變化

## 安裝

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
# 自動選擇模型
python main.py --task "帮我写一个Python函数"

# 指定預算
python main.py --task "review 代码" --budget low

# 列出所有模型
python main.py --list-models

# 指定特定模型
python main.py --task "写一首诗" --model gpt-4
```

### v2.0 新功能

```bash
# 趨勢分析報告
python main.py --trends

# API 測試
python main.py --test-api --provider openai

# 路由學習狀態
python main.py --learning-status

# 迴歸檢測
python main.py --regression-check
```

### 預算選項

| 選項 | 說明 |
|------|------|
| low | 低成本模型優先 |
| balanced | 平衡成本與性能 |
| high | 高性能模型優先 |

## 支援的任務類型

- CODE_GENERATION - 代碼生成
- CODE_REVIEW - 代碼審查
- TEXT_SUMMARIZATION - 文本摘要
- TRANSLATION - 翻譯
- CONVERSATION - 對話
- IMAGE_UNDERSTANDING - 圖像理解
- DATA_ANALYSIS - 數據分析

## 錯誤處理

| 等級 | 類型 | 處理方式 |
|------|------|----------|
| L1 | 輸入錯誤 | 立即返回錯誤訊息 |
| L2 | API 錯誤 | 重試最多 3 次 |
| L3 | 執行錯誤 | 降級到備用模型 |
| L4 | 系統錯誤 | 熔斷，停止請求 |

## 架構

```
model-router/
├── src/
│   ├── classifier.py          # 任務分類器
│   ├── registry.py            # 模型註冊表
│   ├── router.py             # 路由引擎
│   ├── cost_tracker.py       # 成本追蹤
│   ├── trends.py             # 趨勢分析 (v2.0)
│   ├── api_client.py         # API 客戶端 (v2.0)
│   ├── learning.py           # 動態學習 (v2.0)
│   └── regression_detector.py # 迴歸檢測 (v2.0)
├── PLAN.md
├── README.md
└── main.py                   # CLI 入口
```

## License

MIT
"""

__version__ = "2.0.0"
__author__ = "Model Router Team"

from .classifier import TaskClassifier, TaskType
from .registry import ModelRegistry, ModelInfo
from .router import RouterEngine, RouterConfig
from .cost_tracker import CostTracker
from .trends import TrendsAnalyzer, TrendReport
from .api_client import (
    APIClientFactory, 
    test_api_client,
    CompletionResponse,
    APIError,
    AuthenticationError,
    RateLimitError
)
from .learning import RoutingLearner, UserPreference
from .regression_detector import (
    RegressionDetector, 
    ModelHealthReport, 
    RegressionAlert
)

__all__ = [
    # Core
    "TaskClassifier",
    "TaskType", 
    "ModelRegistry",
    "ModelInfo",
    "RouterEngine",
    "RouterConfig",
    "CostTracker",
    # v2.0
    "TrendsAnalyzer",
    "TrendReport",
    "APIClientFactory",
    "test_api_client",
    "CompletionResponse",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "RoutingLearner",
    "UserPreference",
    "RegressionDetector",
    "ModelHealthReport",
    "RegressionAlert",
]
