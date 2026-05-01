# 数据库设计

## 概述

本项目基于 [zvt](https://github.com/zvtvz/zvt) 框架构建，大部分数据存储由 zvt 自动管理。

---

## 数据存储架构

```
data/
├── zvt/                    # zvt 管理的数据（自动）
│   └── zvt.db              # zvt 的 SQLite 数据库
├── my/                     # 业务数据
│   └── invest_assistant.db # 业务数据库（自己管理）
```

---

## zvt 管理的表（无需关心）

zvt 自动创建和维护以下表：

| zvt 表 | 说明 |
|--------|------|
| stock_meta | 股票基本信息 |
| stock_1d_kdata | 日线数据 |
| finance_factor | 财务指标 |
| balance_sheet | 资产负债表 |
| income_statement | 利润表 |
| cash_flow_statement | 现金流量表 |

---

## 业务数据库表（自己管理）

**当前 MVP 版本业务数据较少，主要存在内存中。**

如果后续需要持久化，可使用以下表结构：

### 1. 监控规则（预留）

```sql
-- 监控规则
CREATE TABLE monitor_rules (
    rule_id         TEXT PRIMARY KEY,        -- UUID 字符串
    name            TEXT NOT NULL,
    description     TEXT,
    conditions      TEXT NOT NULL,           -- JSON 格式 [{"field": "pe_ttm", "op": "<", "value": 15}]
    condition_logic TEXT DEFAULT 'AND',
    market          TEXT DEFAULT 'A股',
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_rules_active ON monitor_rules(is_active) WHERE is_active = 1;
```

### 2. 监控事件（预留）

```sql
-- 触发事件记录
CREATE TABLE monitor_events (
    event_id       TEXT PRIMARY KEY,         -- UUID 字符串
    rule_id        TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    trigger_time   TEXT NOT NULL,
    trigger_data   TEXT NOT NULL,            -- JSON 格式快照
    notified       INTEGER DEFAULT 0,
    notified_at    TEXT,
    memo           TEXT,
    FOREIGN KEY (rule_id) REFERENCES monitor_rules(rule_id)
);

CREATE INDEX idx_events_rule ON monitor_events(rule_id);
CREATE INDEX idx_events_time ON monitor_events(trigger_time DESC);
```

---

## 与原设计的对比

| 原设计 | 现状 | 说明 |
|--------|------|------|
| PostgreSQL + Redis | SQLite + zvt | 简化为单机部署 |
| 完整的表结构设计 | 业务表简化 | zvt 接管行情/财务数据 |
| 选股策略表 | 暂存内存 | MVP 阶段简化 |
| 回测结果表 | 用 zvt | zvt.trader 管理 |

---

## 后续扩展

如需持久化更多业务数据，可参考以下扩展：

```sql
-- 选股策略模板
CREATE TABLE screener_strategies (
    strategy_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    criteria   TEXT NOT NULL,  -- JSON
    created_at TEXT DEFAULT (datetime('now'))
);

-- 模拟交易持仓
CREATE TABLE sim_positions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    symbol     TEXT NOT NULL,
    quantity   REAL NOT NULL,
    avg_cost   REAL NOT NULL,
    open_date  TEXT NOT NULL,
    UNIQUE(account_id, symbol)
);

-- 模拟交易记录
CREATE TABLE sim_trades (
    trade_id   TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    symbol     TEXT NOT NULL,
    action     TEXT NOT NULL,  -- buy/sell
    quantity   REAL NOT NULL,
    price      REAL NOT NULL,
    trade_date TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

## SQLite 优势

| 优势 | 说明 |
|------|------|
| 零配置 | 无需安装数据库服务 |
| 本地存储 | 数据完全在本地，符合隐私需求 |
| 够用 | 对于个人项目，SQLite 性能足够 |
| 迁移简单 | 后续可迁移到 PostgreSQL |

---

*文档版本: v0.2*
*最后更新: 2026-05-01*