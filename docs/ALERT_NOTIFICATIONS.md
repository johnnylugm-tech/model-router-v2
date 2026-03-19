# Model Router - Alert Notifications

## 通知方式

Model Router Cost Budget Alert 支援多種通知方式：

### 1. Console 輸出（預設）

```python
from src.cost_budget_alert import CostBudgetAlert

alert = CostBudgetAlert(
    daily_limit=10.0,
    on_alert=lambda msg: print(f"ALERT: {msg}")
)
```

### 2. Webhook

```python
import requests

def webhook_notify(message: str):
    """發送到 Webhook"""
    requests.post(
        "https://hooks.slack.com/services/xxx",
        json={"text": message}
    )

alert = CostBudgetAlert(
    daily_limit=10.0,
    on_alert=webhook_notify
)
```

### 3. Slack

```python
import requests

def slack_notify(message: str):
    """發送到 Slack"""
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {os.getenv('SLACK_TOKEN')}"},
        json={
            "channel": "#alerts",
            "text": f"🚨 {message}"
        }
    )

alert = CostBudgetAlert(
    daily_limit=10.0,
    on_alert=slack_notify
)
```

### 4. Discord

```python
import requests

def discord_notify(message: str):
    """發送到 Discord"""
    requests.post(
        os.getenv("DISCORD_WEBHOOK_URL"),
        json={"content": f"🚨 {message}"}
    )

alert = CostBudgetAlert(
    daily_limit=10.0,
    on_alert=discord_notify
)
```

### 5. Email

```python
import smtplib
from email.mime.text import MIMEText

def email_notify(message: str):
    """發送 Email"""
    msg = MIMEText(message)
    msg["Subject"] = "Model Router Cost Alert"
    msg["From"] = "alerts@example.com"
    msg["To"] = "admin@example.com"
    
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        server.send_message(msg)

alert = CostBudgetAlert(
    daily_limit=10.0,
    on_alert=email_notify
)
```

---

## 完整範例

```python
from src.cost_budget_alert import CostBudgetAlert
import requests

def notify_all(message: str):
    """多管道通知"""
    # Slack
    requests.post(
        os.getenv("SLACK_WEBHOOK"),
        json={"text": f"🚨 {message}"}
    )
    # Discord
    requests.post(
        os.getenv("DISCORD_WEBHOOK"),
        json={"content": f"🚨 {message}"}
    )
    # Log
    print(f"ALERT: {message}")

# 使用
alert = CostBudgetAlert(
    daily_limit=10.0,
    weekly_limit=50.0,
    monthly_limit=200.0,
    warning_threshold=0.8,
    on_alert=notify_all
)

# 記錄成本
alert.record("gpt-4o", input_tokens=1000, output_tokens=500)
```

---

## 環境變數

```bash
# Slack
export SLACK_WEBHOOK="https://hooks.slack.com/services/xxx"

# Discord
export DISCORD_WEBHOOK="https://discord.com/api/webhooks/xxx"

# Email
export EMAIL_USER="user@gmail.com"
export EMAIL_PASS="password"
```
