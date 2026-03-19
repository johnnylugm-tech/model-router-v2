# Model Router - API Documentation

> Version: 1.0.0

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [CLI Usage](#cli-usage)
4. [Python API](#python-api)
5. [Configuration](#configuration)
6. [Smart Cache](#smart-cache)
7. [Failover](#failover)
8. [Rate Limiting](#rate-limiting)
9. [Cost Tracking](#cost-tracking)
10. [Environment Variables](#environment-variables)

---

## Installation

```bash
git clone https://github.com/johnnylugm-tech/model-router-v2.git
cd model-router-v2
pip install -r requirements.txt
```

### Docker

```bash
docker build -t model-router .
docker run -p 8080:8080 model-router
```

---

## Quick Start

### CLI

```bash
python main.py --task "幫我寫一個Python函數"
python main.py --task "翻譯這段文字" --budget low
python main.py --list-models
```

### Python

```python
from src.router import ModelRouter

router = ModelRouter()
result = router.route(task="你的任務", budget="balanced")
print(result)
```

---

## CLI Usage

```bash
python main.py [OPTIONS]

Options:
  -t, --task TEXT              任務描述
  -m, --model TEXT             指定模型 ID
  -b, --budget {low,balanced,high,auto}
                                預算等級
  --list-models                列出所有可用模型
  --list-tasks                 列出所有任務類型
  --test-api                   測試 API 連接
  --test-failover              測試 Failover
  --stats                      顯示成本統計
  --trends                     顯示趨勢分析
  --cache-stats                顯示快取統計
  --show-config                顯示配置
```

---

## Python API

### ModelRouter

```python
from src.router import ModelRouter

router = ModelRouter(config_path="config.yaml")
```

#### Methods

##### route(task, model=None, budget='balanced', **kwargs)

執行路由並返回結果。

```python
result = router.route(
    task="你的任務",
    model="gpt-4o",        # 可選
    budget="balanced",      # low, balanced, high, auto
    temperature=0.7,        # 可選
    max_tokens=1000         # 可選
)

print(result.content)  # 回應內容
print(result.model)    # 使用的模型
print(result.cost)      # 成本
```

##### list_models()

列出所有可用模型。

```python
models = router.list_models()
for provider, model_list in models.items():
    print(f"{provider}: {model_list}")
```

##### get_model(model_id)

獲取特定模型信息。

```python
model = router.get_model("gpt-4o")
print(model.name, model.price_input, model.price_output)
```

### SmartCache

```python
from src.smart_cache import SmartCache

cache = SmartCache(
    similarity_threshold=0.9,  # 相似度閾值
    ttl=86400,                 # TTL 秒數 (預設 24 小時)
    db_path="./data/cache.db"  # SQLite 路徑
)
```

#### Methods

##### get(prompt)

獲取快取。

```python
cached = cache.get("你的prompt")
if cached:
    print(cached.content)
```

##### set(prompt, response)

設置快取。

```python
cache.set("你的prompt", response)
```

##### get_stats()

獲取統計。

```python
stats = cache.get_stats()
print(stats.hit_rate, stats.total_requests)
```

### RateLimiter

```python
from src.rate_limiter import RateLimiter, RateLimit, Quota

limiter = RateLimiter(
    rate_limit=RateLimit(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000
    ),
    quota=Quota(
        daily_limit=10000,
        monthly_limit=100000
    )
)
```

#### Methods

##### check(user_id='default')

檢查是否允許請求。

```python
result = limiter.check("user_001")
if result.allowed:
    print("允許請求")
else:
    print(f"被限制: {result.reason}")
```

### CostBudgetAlert

```python
from src.cost_budget_alert import CostBudgetAlert

alert = CostBudgetAlert(
    daily_limit=10.0,    # 每日上限 $10
    weekly_limit=50.0,   # 每週上限 $50
    monthly_limit=200.0,  # 每月上限 $200
    warning_threshold=0.8  # 80% 警告
)
```

#### Methods

##### record(model, input_tokens, output_tokens)

記錄成本。

```python
alert.record("gpt-4o", input_tokens=100, output_tokens=50)
```

##### check_budget()

檢查預算。

```python
status = alert.check_budget()
print(status.daily_used, status.daily_limit)
```

### LLM Gateway

```python
from src.llm_gateway import LLMGateway, GatewayConfig

gateway = LLMGateway(
    config=GatewayConfig(
        host="0.0.0.0",
        port=8080,
        require_auth=True
    )
)
```

#### Start Gateway

```python
gateway.run()  # 阻塞
# 或
gateway.run_background()  # 後台
```

#### API Endpoints

```
POST /v1/chat/completions
GET  /v1/models
POST /v1/keys
GET  /v1/stats
```

---

## Configuration

### config.yaml

```yaml
routing:
  defaults:
    primary: gpt-4o-mini
    fallback:
      - gpt-4o
      - gemini-1.5-flash
      - claude-3-5-sonnet
  
  task_overrides:
    CODE_GENERATION: claude-3-5-sonnet
    CODE_REVIEW: claude-3-5-sonnet
    CONVERSATION: gpt-4o-mini
    DATA_ANALYSIS: gpt-4o
    TEXT_SUMMARIZATION: gemini-1.5-flash
    TRANSLATION: minimax-abab6.5s-chat

failover:
  enabled: true
  max_retries: 3
  retry_delay: 1.0

cache:
  enabled: true
  similarity_threshold: 0.9
  ttl: 86400
```

---

## Smart Cache

### 機制

| 項目 | 說明 |
|------|------|
| 相似度算法 | Jaccard Similarity |
| 閾值 | 0.9 (可配置) |
| 儲存 | SQLite |
| TTL | 24 小時 (可配置) |

### 效能

| 指標 | 數值 |
|------|------|
| 命中率（預估） | 20-50% |
| 節省成本 | 30-50% |

---

## Failover

### 觸發條件

| 條件 | 動作 |
|------|------|
| Timeout (>30s) | 切換下一個模型 |
| Rate Limit (429) | 等待後重試 |
| Server Error (5xx) | 切換下一個模型 |
| Auth Error (401) | 立即失敗 |

### 流程

```
請求 → 模型 A → 失敗 → 重試 (最多3次)
                ↓
            失敗 → 模型 B → 成功 → 返回結果
                ↓
            失敗 → 模型 C → 成功 → 返回結果
                ↓
            全部失敗 → 返回錯誤
```

---

## Rate Limiting

### 限制級別

| 級別 | 預設值 |
|------|--------|
| per-minute | 60 |
| per-hour | 1,000 |
| per-day | 10,000 |

### 回應

```json
{
  "allowed": false,
  "reason": "rate_limit_minute",
  "next_available_in": 30
}
```

---

## Cost Tracking

### 計算公式

```
成本 = (input_tokens / 1M * price_input) + (output_tokens / 1M * price_output)
```

### 支援模型定價

| 模型 | Input ($/M) | Output ($/M) |
|------|-------------|--------------|
| gpt-4o | $5.00 | $15.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| claude-3-5-sonnet | $3.00 | $15.00 |
| gemini-1.5-flash | $0.075 | $0.30 |

---

## Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google
export GOOGLE_API_KEY="AIza..."

# MiniMax
export MINIMAX_API_KEY="..."
```

---

## Examples

### 基本使用

```python
from src.router import ModelRouter

router = ModelRouter()
result = router.route(task="Hello, how are you?")
print(result.content)
```

### 指定預算

```python
result = router.route(task="寫一個函數", budget="low")
```

### 自定義 Failback

```python
result = router.route(
    task="翻譯",
    fallback=["claude-3-5-sonnet", "gemini-1.5-flash"]
)
```

### 使用快取

```python
from src.smart_cache import SmartCache

cache = SmartCache()
cached = cache.get("我的prompt")
if not cached:
    result = router.route(task="我的prompt")
    cache.set("我的prompt", result)
```

---

## License

MIT
