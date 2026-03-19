# Model Router MVP 開發計劃

## 階段 1: 核心基礎設施

### 1.1 模型註冊表 (Model Registry)
- [x] 定義模型數據結構
- [x] 實現模型配置管理
- [x] 支援 OpenAI, Anthropic, Google, MiniMax

### 1.2 任務分類器 (Task Classifier)
- [x] 基於關鍵詞的任務類型識別
- [x] 支援 7 種任務類型
- [x] 置信度計算

### 1.3 路由引擎 (Router Engine)
- [x] ReAct 設計模式實現
- [x] L1-L4 錯誤處理
- [x] 成本和延遲感知路由

## 階段 2: CLI 工具

### 2.1 命令行界面
- [x] --task: 任務描述
- [x] --model: 模型選擇 (auto/low/balanced/high)
- [x] --list-models: 列出所有模型

## 階段 3: 擴展功能

### 3.1 成本追蹤
- [x] 請求計數
- [x] 成本計算

### 3.2 錯誤處理
- [x] L1: 輸入驗證
- [x] L2: API 重試
- [x] L3: 降級處理
- [x] L4: 熔斷機制

## 驗收標準

- [ ] CLI 正常運行
- [ ] 任務分類準確
- [ ] 模型選擇合理
- [ ] 錯誤處理正確
