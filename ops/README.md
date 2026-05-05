# Invest Assistant

个人投资助理 - 基本面量化监控系统

## 功能

- 📊 **监控预警**: 按财务指标（PE、ROE等）监控股票，满足条件时自动通知
- 🔍 **选股工具**: 多条件筛选股票，支持价值投资、成长股策略
- 📈 **数据同步**: 自动从东方财富获取A股/港股数据
- 🔔 **通知推送**: 支持 Email、Telegram 通知

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 同步数据

```bash
python -m invest_assistant.data.sync
```

### 3. 启动服务

```bash
uvicorn invest_assistant.main:app --reload
```

### 4. 打开 API 文档

浏览器访问: http://localhost:8000/docs

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/stocks/ | 获取股票列表 |
| GET | /api/v1/stocks/{symbol} | 查询股票信息 |
| GET | /api/v1/stocks/{symbol}/financial | 查询财务指标 |
| POST | /api/v1/stocks/screen | 筛选股票 |
| GET | /api/v1/monitor/rules | 查看监控规则 |
| POST | /api/v1/monitor/rules | 添加监控规则 |
| POST | /api/v1/monitor/check | 手动触发检查 |
| POST | /api/v1/sync/all | 同步所有数据 |

## 配置

创建 `.env` 文件：

```env
# 数据目录
DATA_DIR=./data

# 通知 - Email
NOTIFICATION_EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your_password
NOTIFICATION_EMAIL_TO=target@email.com

# 通知 - Telegram
NOTIFICATION_TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 监控规则示例

```bash
# 添加低估值监控规则 (PE < 15 且 ROE > 10)
curl -X POST http://localhost:8000/api/v1/monitor/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "低估价值股",
    "conditions": [
      {"field": "pe_ttm", "op": "<", "value": 15},
      {"field": "roe", "op": ">", "value": 10}
    ],
    "condition_logic": "AND"
  }'
```

## 项目结构

```
invest_assistant/
├── src/invest_assistant/
│   ├── api/           # API 接口
│   ├── core/          # 核心业务逻辑
│   │   ├── monitor/   # 监控引擎
│   │   └── notification/  # 通知推送
│   ├── data/          # 数据层（封装 zvt）
│   ├── services/      # 业务服务
│   └── models/        # 数据模型
└── data/              # 数据存储
    ├── zvt/           # zvt 数据
    └── my/            # 业务数据
```

## 技术栈

- **数据**: zvt (东方财富/聚宽)
- **API**: FastAPI
- **定时任务**: APScheduler
- **通知**: Email, Telegram

## License

MIT