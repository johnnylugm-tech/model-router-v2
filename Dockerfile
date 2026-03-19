# Model Router - Dockerfile

FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 複製依賴文件
COPY requirements.txt .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程序
COPY . .

# 創建數據目錄
RUN mkdir -p data

# 暴露端口
EXPOSE 8080

# 啟動命令
CMD ["python", "main.py"]

# 或者啟動 Gateway
# CMD ["python", "-c", "from src.llm_gateway import LLMGateway, GatewayConfig; LLMGateway(GatewayConfig(port=8080)).run()"]
