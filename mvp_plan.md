# MVP 实现计划

## 状态：已完成 ✅

MVP 版本已于 2026-05-01 完成开发。

---

## 目标

**2周内**做出一个能跑起来的监控预警系统：
- 自动同步数据（zvt + eastmoney 免费数据源）
- 按规则监控股票
- 满足条件时发送通知

---

## 实际完成情况

### 周1：数据 + 监控引擎

| Day | 计划 | 完成情况 |
|-----|------|----------|
| 1-2 | 项目搭建 + 数据同步 | ✅ 完成 |
| 3-4 | 监控引擎核心逻辑 | ✅ 完成 |
| 5 | 数据查询封装 | ✅ 完成 |

**完成内容**:
- 项目结构创建 (`invest_assistant/`)
- `data/sync.py` - 数据同步（调用 zvt EastmoneyRecorders）
- `data/provider.py` - 数据查询封装
- `core/monitor/engine.py` - 监控引擎核心逻辑
- `core/monitor/evaluator.py` - 条件评估器

### 周2：通知 + API

| Day | 计划 | 完成情况 |
|-----|------|----------|
| 6-7 | 通知推送 | ✅ 完成 |
| 8-9 | 定时任务 + API | ✅ 完成 |
| 10-11 | 测试 + 文档 | ✅ 完成 |

**完成内容**:
- `core/notification/sender.py` - Email/Telegram 通知
- `api/monitor.py` - 监控相关 API
- `api/stocks.py` - 股票查询 API
- `api/sync.py` - 数据同步 API
- `main.py` - FastAPI 入口 + APScheduler 定时任务

---

## 技术栈

| 模块 | 技术 |
|------|------|
| 数据获取 | zvt (eastmoney 免费数据源) |
| 数据库 | SQLite（zvt 自动管理） |
| API | FastAPI |
| 定时任务 | APScheduler |
| 通知 | Email / Telegram |

---

## 代码量

| 模块 | 行数 |
|------|------|
| 监控引擎 | ~100 |
| 通知推送 | ~80 |
| API 接口 | ~150 |
| 数据封装 | ~120 |
| **总计** | ~450 |

---

## 快速启动

```bash
cd invest_assistant

# 安装依赖
pip install -r requirements.txt

# 同步数据
python -c "from invest_assistant.data import sync_all; sync_all()"

# 启动服务
uvicorn invest_assistant.main:app --reload

# 打开文档 http://localhost:8000/docs
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/stocks/ | 获取股票列表 |
| GET | /api/v1/stocks/{symbol} | 查询股票信息 |
| GET | /api/v1/stocks/{symbol}/kline | 查询日线数据 |
| GET | /api/v1/stocks/{symbol}/financial | 查询财务指标 |
| POST | /api/v1/stocks/screen | 筛选股票 |
| GET | /api/v1/monitor/rules | 查看监控规则 |
| POST | /api/v1/monitor/rules | 添加监控规则 |
| DELETE | /api/v1/monitor/rules/{rule_id} | 删除规则 |
| POST | /api/v1/monitor/check | 手动触发检查 |
| GET | /api/v1/monitor/events | 查看触发事件 |
| POST | /api/v1/sync/all | 同步所有数据 |

---

## 下一步计划

| 优先级 | 功能 | 说明 |
|--------|------|------|
| 高 | 添加更多通知渠道 | 钉钉、企业微信 |
| 高 | 完善选股工具 | 多策略模板 |
| 中 | 添加回测功能 | 使用 zvt.trader |
| 中 | Web UI 界面 | 使用 Vue/React |
| 低 | 模拟交易 | 使用 zvt.trader |
| 低 | 组合管理 | 持仓跟踪 |

---

*文档版本: v0.2*
*最后更新: 2026-05-01*