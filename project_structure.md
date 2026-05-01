# 项目结构

## 实际项目结构

```
invest_assistant/
├── src/
│   └── invest_assistant/
│       ├── __init__.py
│       ├── main.py                    # FastAPI 入口 + 定时任务
│       ├── config.py                  # 配置管理
│       │
│       ├── api/                       # API 接口层
│       │   ├── __init__.py
│       │   ├── monitor.py            # 监控 API
│       │   ├── stocks.py             # 股票查询 API
│       │   └── sync.py               # 数据同步 API
│       │
│       ├── core/                      # 核心业务逻辑（自己写）
│       │   ├── __init__.py
│       │   ├── monitor/               # ⭐ 监控引擎
│       │   │   ├── __init__.py
│       │   │   └── engine.py          # 监控引擎核心
│       │   └── notification/          # ⭐ 通知推送
│       │       ├── __init__.py
│       │       └── sender.py          # Email/Telegram 发送
│       │
│       ├── services/                  # 业务服务（调用 zvt）
│       │   ├── __init__.py
│       │   └── screener.py           # 选股服务
│       │
│       ├── data/                      # 数据层（封装 zvt）
│       │   ├── __init__.py
│       │   ├── provider.py            # 数据查询封装
│       │   └── sync.py               # 数据同步任务
│       │
│       └── models/                    # 数据模型
│           ├── __init__.py
│           ├── schemas.py             # Pydantic 模型
│           └── api_models.py         # API 请求/响应模型
│
├── data/                               # 数据存储
│   ├── zvt/                          # zvt 数据（自动管理）
│   └── my/                           # 业务数据
│
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 与 zvt 的关系

```
┌─────────────────────────────────────────────────────────────┐
│                    invest_assistant                         │
├─────────────────────────────────────────────────────────────┤
│  api/          │  FastAPI 接口（自己写）                      │
│  core/         │  监控引擎 + 通知（自己写）                   │
│  services/     │  业务服务（调用 zvt）                        │
│  data/         │  数据封装（调用 zvt）                        │
├─────────────────────────────────────────────────────────────┤
│                         zvt                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  recorders/    │  数据获取（eastmoney 等）            │   │
│  │  api/          │  数据查询（query_kdata 等）         │   │
│  │  factors/      │  因子计算（选股用）                  │   │
│  │  trader/       │  回测引擎                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 代码量分布

| 模块 | 行数 | 说明 |
|------|------|------|
| 自己写的核心 | ~350 | 监控引擎、通知、API |
| 调用 zvt 的封装 | ~150 | 数据查询、同步 |
| zvt 框架 | - | 开源框架，不需要写 |
| **总计** | ~500 | MVP 版本 |

---

## 工作量分配

```
自己开发:
  ├── 监控引擎 (core/monitor/engine.py)
  ├── 通知推送 (core/notification/sender.py)
  └── API 接口 (api/*.py)

调用 zvt:
  ├── 数据获取 (data/sync.py)
  ├── 数据查询 (data/provider.py)
  └── 选股 (services/screener.py)
```

---

## 核心模块说明

### 1. 监控引擎 (core/monitor/engine.py)

```python
class MonitorEngine:
    """监控引擎核心"""

    def check_rule(self, rule):
        """检查单条规则，返回触发股票"""
        ...

    def check_all_rules(self):
        """检查所有规则，发送通知"""
        ...
```

### 2. 通知推送 (core/notification/sender.py)

```python
class NotificationSender:
    """通知发送器"""

    def send(self, rule_name, stocks, conditions):
        """发送通知（Email/Telegram）"""
        ...
```

### 3. 数据封装 (data/provider.py)

```python
def query_all_financial_metrics(market="A股"):
    """查询市场所有股票的财务数据"""
    ...

def query_daily_kdata(symbol, start_date, end_date):
    """查询日线数据"""
    ...
```

---

## 启动流程

```python
# main.py
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()
scheduler = BackgroundScheduler()

# 定时执行监控检查
scheduler.add_job(run_monitor_check, "cron", hour="10,11,12,13,14", minute="0")
scheduler.add_job(run_monitor_check, "cron", hour="16", minute="30")

scheduler.start()
```

---

## 扩展方式

### 添加新的通知渠道

```python
# core/notification/sender.py
class NotificationSender:
    def _send_dingtalk(self, message):
        """钉钉通知"""
        ...
```

### 添加新的选股策略

```python
# services/screener.py
class StockScreener:
    def screen_by_value(self, pe_max, roe_min):
        """价值投资策略"""
        ...

    def screen_by_growth(self, revenue_yoy_min):
        """成长股策略"""
        ...
```

---

## 依赖关系

```
main.py
  ├── api/monitor.py → core/monitor/engine.py
  ├── api/stocks.py → data/provider.py
  ├── api/sync.py → data/sync.py
  ├── core/monitor/engine.py → data/provider.py
  ├── core/monitor/engine.py → core/notification/sender.py
  └── services/screener.py → data/provider.py
```

---

*文档版本: v0.2*
*最后更新: 2026-05-01*