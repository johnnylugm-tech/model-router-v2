# Model Router v1.0.0 - 發布日誌

> 發布日期：2026-03-19

---

## 🎉 v1.0.0 - 首次發布

Model Router 是一款智慧模型路由系統，幫助你自動選擇最適合的 LLM 模型。

---

### ✨ 核心功能

| 功能 | 說明 |
|------|------|
| **智慧路由** | 根據任務自動選擇最適合的模型 |
| **成本優化** | 預算感知路由，省錢首選 |
| **Failover** | 自動備援，確保服務不中斷 |
| **語意快取** | Smart Cache 減少重複請求 |
| **請求批處理** | Batch Processor 提升效率 |
| **成本預警** | Cost Budget Alert 監控開支 |
| **流量控制** | Rate Limiter 保護 API 配額 |
| **連接池** | Connection Pool 優化效能 |
| **審計日誌** | Audit Logger 完整記錄 |
| **監控整合** | Prometheus Exporter 導出指標 |
| **API 閘道** | LLM Gateway 統一入口 |

---

### 🌐 支援模型

| 提供商 | 模型 |
|--------|------|
| **OpenAI** | GPT-4o, GPT-4o Mini, GPT-4 Turbo, GPT-3.5 Turbo |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku |
| **Google** | Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 3.1 Pro |
| **MiniMax** | Kimi K2.5, Abab 6.5s, Abab 6.5g |
| **DeepSeek** | V4, V3 |

---

### 📦 安裝

```bash
git clone https://github.com/johnnylugm-tech/model-router-v2.git
cd model-router-v2
pip install -r requirements.txt
```

---

### 🚀 使用方式

```bash
# 基本使用
python main.py --task "幫我寫一個Python函數"

# 指定預算
python main.py --task "分析數據" --budget low

# 指定模型
python main.py --task "代码审查" --model claude-3-5-sonnet

# 查看模型列表
python main.py --list-models

# 測試 Failover
python main.py --test-failover
```

---

### 📁 專案結構

```
model-router/
├── main.py              # CLI 入口
├── config.yaml          # 配置文件
├── src/
│   ├── router.py       # 路由邏輯
│   ├── classifier.py   # 任務分類
│   ├── failover.py     # Failover
│   ├── api_client.py   # API 客戶端
│   ├── smart_cache.py  # 智慧快取
│   ├── batch_processor.py
│   ├── cost_budget_alert.py
│   ├── rate_limiter.py
│   ├── connection_pool.py
│   ├── audit_logger.py
│   ├── prometheus_exporter.py
│   ├── llm_gateway.py
│   └── registry.py
└── tests/
```

---

### 🔧 配置

編輯 `config.yaml` 來自定義：
- 預設模型
- Failover 策略
- Rate Limit 設置
- 預算限制

---

### 📝 更新日誌

| 版本 | 日期 | 說明 |
|------|------|------|
| v1.0.0 | 2026-03-19 | 首次發布 |

---

** Enjoy! 🚀 **
