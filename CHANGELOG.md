# Model Router v3.0.0 更新日誌

> 發布日期：2026-03-19

---

## 🎉 v3.0.0 - 重大更新

### 新增功能

| 功能 | 檔案 | 說明 |
|------|------|------|
| **Smart Cache** | `src/smart_cache.py` | 智慧快取（SQLite + TTL + 相似匹配）|
| **Batch Processor** | `src/batch_processor.py` | 請求批處理 + 並行處理 |
| **Cost Budget Alert** | `src/cost_budget_alert.py` | 成本預警 + 自動降級建議 |
| **Rate Limiter** | `src/rate_limiter.py` | 流量控制 + 配額管理 |
| **Connection Pool** | `src/connection_pool.py` | HTTP 連接池 + 重試機制 |
| **Audit Logger** | `src/audit_logger.py` | 審計日誌 + 查詢 |
| **Prometheus Exporter** | `src/prometheus_exporter.py` | Prometheus 指標導出 |
| **LLM Gateway** | `src/llm_gateway.py` | 統一 API 閘道 |
| **Model Registry** | `src/registry.py` | 模型註冊表 |

### 新增模型支援

| 提供商 | 模型 |
|--------|------|
| Google | Gemini 3.1 Pro |
| MiniMax | Kimi K2.5 |
| DeepSeek | V4, V3 |

---

## v2.3.0 更新

### 新增
- Gemini 3.1 支援
- Kimi K2.5 支援
- Model Registry 模組

---

## v2.2.1 更新

### 新增
- Semantic Cache 基礎版
- 測試檔案

---

## v2.2.0 更新

### 新增
- DeepSeek V4 支援
- Semantic Cache

---

## v2.1.0 更新

### 新增
- 完整智慧路由系統
- 趨勢分析
- 學習功能
- Failover

---

*Generated: 2026-03-19*
