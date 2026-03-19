# Model Router

智慧模型路由系統 - 根據任務類型自動選擇最適合的 AI 模型

![Version](https://img.shields.io/badge/version-2.1.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)

## 功能特性

| 功能 | 說明 |
|------|------|
| **任務分類器** | 自動識別 7 種任務類型 |
| **模型註冊表** | 支援 OpenAI, Anthropic, Google, MiniMax |
| **智能路由** | 基於成本、延遲、任務特性選擇最佳模型 |
| **錯誤處理** | L1-L4 四級錯誤處理機制 |
| **趨勢分析** | 追蹤任務分佈、模型使用、成本趨勢 |
| **API 整合** | 統一客戶端支援多種提供商 |
| **動態學習** | 基於歷史優化路由決策 |
| **迴歸檢測** | 監控模型品質變化 |

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

# 顯示版本
python main.py --version
```

### v2.0 新功能

```bash
# 趨勢分析報告 (最近 7 天)
python main.py --trends

# API 測試
python main.py --test-api --provider openai
python main.py --test-api --provider anthropic
python main.py --test-api --provider minimax
python main.py --test-api --provider gemini

# 路由學習狀態
python main.py --learning-status

# 迴歸檢測
python main.py --regression-check
```

### v2.1 新功能

```bash
# 指定預算路由
python main.py --task "翻譯" --budget low
python main.py --task "複雜推理" --budget high

# 顯示配置
python main.py --show-config

# 測試 Failover
python main.py --test-failover

# 指定 Fallback
python main.py --task "寫代碼" --fallback gpt-4o,gemini-1.5-flash
```

### 預算選項

| 選項 | 說明 |
|------|------|
| low | 低成本模型優先 |
| balanced | 平衡成本與性能 |
| high | 高性能模型優先 |
| auto | 根據任務類型自動選擇 |

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
| L3 | Rate Limit | 指數退避重試最多 5 次 |
| L4 | 執行錯誤 | 降級到備用模型 |
| L5 | 系統錯誤 | 熔斷，停止請求 |

## 架構

```
model-router/
├── src/
│   ├── classifier.py           # 任務分類器
│   ├── registry.py             # 模型註冊表
│   ├── router.py               # 路由引擎 (v2.1: TaskAwareRouter)
│   ├── cost_tracker.py         # 成本追蹤
│   ├── trends.py               # 趨勢分析 (v2.0)
│   ├── api_client.py           # API 客戶端 (v2.0)
│   ├── learning.py             # 動態學習 (v2.0)
│   ├── regression_detector.py # 迴歸檢測 (v2.0)
│   ├── config.py               # 配置管理 (v2.1)
│   └── failover.py             # 自動 Failover (v2.1)
├── PLAN.md
├── COMPETITIVE_ANALYSIS.md
├── README.md
├── config.yaml                 # 配置文件 (v2.1)
└── main.py                     # CLI 入口
```

## v2.0 新增模組

### trends.py - 趨勢分析儀表板

追蹤並分析：
- 任務類型分佈
- 模型使用頻率
- 成本趨勢
- 生成詳細報告

### api_client.py - API 整合優化

統一客戶端支援：
- OpenAI (GPT-4o, GPT-4o Mini, etc.)
- Anthropic (Claude Sonnet, Claude Opus)
- MiniMax (Abab 6.5s, Abab 6.5g)
- Gemini (Gemini 2.0, Gemini 1.5)

標準化錯誤處理：
- AuthenticationError
- RateLimitError
- InvalidRequestError
- TimeoutError

### learning.py - 動態路由學習

功能：
- 記錄任務歷史
- 學習用戶偏好
- 基於歷史優化路由決策
- 用戶評分系統

### regression_detector.py - LLM 迴歸檢測

功能：
- 監控輸出品質變化
- 及時發現模型退化
- 自動告警 (warning/critical)
- 模型健康報告

## v2.1 新增模組

### config.py - 模型分層配置

功能：
- 支援 YAML 配置文件
- 定義模型層級：primary, fallback, heartbeat, subagent
- 支援任務覆寫 (task_overrides)
- 配置熱重載

配置格式：
```yaml
routing:
  defaults:
    primary: "gpt-4o-mini"
    fallback:
      - "gpt-4o"
      - "gemini-1.5-flash"
  task_overrides:
    CODE_REVIEW: "claude-3-5-sonnet"
    TRANSLATION: "minimax-abab6.5s-chat"
```

### failover.py - 自動 Failover 系統

功能：
- 自動偵測 API 錯誤
- 自動切換到 Fallback Provider
- 支援 RateLimit 指數退避重試
- 完整的錯誤分類 (L1-L5)
- 熔斷機制

錯誤分類：
- L1_INPUT: 輸入錯誤 (不重試)
- L2_API: API 錯誤 (可重試)
- L3_RATE_LIMIT: Rate Limit (指數退避)
- L4_EXECUTION: 執行錯誤 (有限重試)
- L5_SYSTEM: 系統錯誤 (熔斷)

### TaskAwareRouter - 任務感知定價

功能：
- 根據任務複雜度選擇模型
- 支援 budget 參數 (low/medium/high)
- 自動優化成本
- 任務複雜度評估

## License

MIT
