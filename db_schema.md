# 数据库设计

## 概述

本数据库用于支撑基本面量化投资助理系统，核心场景：
- 日度行情存储（技术面分析）
- 财务数据存储（基本面分析）
- 监控规则与事件触发
- 策略回测数据
- 模拟交易记录

---

## 表结构

### 1. 股票基础信息

```sql
-- 股票/ETF/期货等标的物基本信息
CREATE TABLE symbols (
    symbol          VARCHAR(20) PRIMARY KEY,   -- 股票代码，如 000001.SZ
    name            VARCHAR(100) NOT NULL,    -- 股票名称
    exchange        VARCHAR(10) NOT NULL,    -- 交易所，如 SSE/SZSE/HKEX
    market          VARCHAR(10) NOT NULL,    -- 市场，如 A股/港股/美股
    instrument_type VARCHAR(20) NOT NULL,    -- 类型，如 stock/etf/futures
    list_date       DATE,                    -- 上市日期
    delist_date     DATE,                    -- 退市日期，NULL表示未退市
    is_active       BOOLEAN DEFAULT TRUE,    -- 是否在交易
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_symbols_market ON symbols(market);
CREATE INDEX idx_symbols_exchange ON symbols(exchange);
CREATE INDEX idx_symbols_active ON symbols(is_active) WHERE is_active = TRUE;
```

---

### 2. 日线行情数据（技术面）

```sql
-- 日线K线数据
CREATE TABLE daily_bars (
    symbol      VARCHAR(20) NOT NULL,
    trade_date  DATE NOT NULL,
    open        DECIMAL(10, 3),
    high        DECIMAL(10, 3),
    low         DECIMAL(10, 3),
    close       DECIMAL(10, 3),
    volume      BIGINT,
    amount      DECIMAL(20, 2),
    turns       DECIMAL(10, 4),
    PRIMARY KEY (symbol, trade_date)
);

CREATE INDEX idx_daily_bars_date ON daily_bars(trade_date);
CREATE INDEX idx_daily_bars_symbol ON daily_bars(symbol);

-- 复权因子（用于前复权计算）
CREATE TABLE split_adjust (
    symbol      VARCHAR(20) NOT NULL,
    ex_date     DATE NOT NULL,           -- 除权日期
    split_ratio DECIMAL(10, 6),           -- 拆分比例，如 10 送 10 则为 0.5
    dividend    DECIMAL(10, 4),           -- 分红，每股分红金额
    PRIMARY KEY (symbol, ex_date)
);
```

---

### 3. 财务数据（基本面）

```sql
-- 财务指标（TTM/单季/年报）
CREATE TABLE financial_metrics (
    symbol              VARCHAR(20) NOT NULL,
    period_end          DATE NOT NULL,      -- 财报期间
    announce_date       DATE,                -- 公告日期
    period_type         VARCHAR(10) NOT NULL, -- 财报类型: Q1/Q2/Q3/Q4/TTM
    -- 盈利能力
    roe                 DECIMAL(10, 4),      -- 净资产收益率 %
    roe_diluted         DECIMAL(10, 4),
    roa                 DECIMAL(10, 4),
    gross_margin        DECIMAL(10, 4),     -- 毛利率 %
    net_margin          DECIMAL(10, 4),      -- 净利率 %
    eps_basic           DECIMAL(10, 4),      -- 每股收益
    eps_diluted         DECIMAL(10, 4),
    bps                 DECIMAL(10, 4),      -- 每股净资产
    -- 成长性
    revenue_yoy         DECIMAL(10, 4),     -- 营收增速 %
    net_income_yoy      DECIMAL(10, 4),     -- 净利润增速 %
    -- 财务健康
    debt_to_asset_ratio DECIMAL(10, 4),     -- 资产负债率 %
    inventory_turnover  DECIMAL(10, 4),
    ocfps               DECIMAL(10, 4),      -- 每股经营现金流
    operating_cash_to_revenue DECIMAL(10, 4),
    PRIMARY KEY (symbol, period_end, period_type)
);

CREATE INDEX idx_metrics_period ON financial_metrics(period_end);
CREATE INDEX idx_metrics_symbol ON financial_metrics(symbol);

-- 估值指标历史（PE/PB/PS 等）
CREATE TABLE price_ratios (
    symbol      VARCHAR(20) NOT NULL,
    trade_date  DATE NOT NULL,
    pe_ttm      DECIMAL(10, 2),           -- 市盈率TTM
    pe_lyr      DECIMAL(10, 2),           -- 市盈率LYR
    pb          DECIMAL(10, 2),            -- 市净率
    ps_ttm      DECIMAL(10, 2),            -- 市销率TTM
    pcfr        DECIMAL(10, 2),            -- 市现率
    dividend_yield DECIMAL(10, 4),         -- 股息率 %
    PRIMARY KEY (symbol, trade_date)
);

CREATE INDEX idx_ratios_date ON price_ratios(trade_date);
```

---

### 4. 财务报表原始数据

```sql
-- 资产负债表
CREATE TABLE balance_sheet (
    symbol              VARCHAR(20) NOT NULL,
    period_end          DATE NOT NULL,
    announce_date       DATE,
    period_type         VARCHAR(10) NOT NULL,
    -- 资产
    total_assets        DECIMAL(20, 2),
    total_current_assets DECIMAL(20, 2),
    total_non_current_assets DECIMAL(20, 2),
    cash_and_equivalents DECIMAL(20, 2),
    accounts_receivable  DECIMAL(20, 2),
    inventory            DECIMAL(20, 2),
    fixed_assets         DECIMAL(20, 2),
    intangible_assets    DECIMAL(20, 2),
    goodwill             DECIMAL(20, 2),
    -- 负债
    total_liabilities    DECIMAL(20, 2),
    total_current_liabilities DECIMAL(20, 2),
    total_non_current_liabilities DECIMAL(20, 2),
    short_term_borrowing DECIMAL(20, 2),
    long_term_borrowing  DECIMAL(20, 2),
    accounts_payable     DECIMAL(20, 2),
    -- 权益
    total_equity         DECIMAL(20, 2),
    equity_attributable  DECIMAL(20, 2),
    minority_interest    DECIMAL(20, 2),
    retained_earnings    DECIMAL(20, 2),
    PRIMARY KEY (symbol, period_end, period_type)
);

-- 利润表
CREATE TABLE income_statement (
    symbol              VARCHAR(20) NOT NULL,
    period_end          DATE NOT NULL,
    announce_date       DATE,
    period_type         VARCHAR(10) NOT NULL,
    revenue             DECIMAL(20, 2),
    operating_profit    DECIMAL(20, 2),
    total_profit        DECIMAL(20, 2),
    net_income          DECIMAL(20, 2),
    net_income_attributable DECIMAL(20, 2),
    basic_eps           DECIMAL(10, 4),
    diluted_eps         DECIMAL(10, 4),
    -- 费用
    operating_cost      DECIMAL(20, 2),
    selling_expense     DECIMAL(20, 2),
    admin_expense       DECIMAL(20, 2),
    financial_expense   DECIMAL(20, 2),
    rd_expense          DECIMAL(20, 2),
    -- 其他
    income_tax          DECIMAL(20, 2),
    non_operating_income DECIMAL(20, 2),
    non_operating_expense DECIMAL(20, 2),
    PRIMARY KEY (symbol, period_end, period_type)
);

-- 现金流量表
CREATE TABLE cash_flow (
    symbol              VARCHAR(20) NOT NULL,
    period_end          DATE NOT NULL,
    announce_date       DATE,
    period_type         VARCHAR(10) NOT NULL,
    PRIMARY KEY (symbol, period_end, period_type)
    -- 字段根据 TickFlow 实际返回补充
);
```

---

### 5. 监控规则与事件

```sql
-- 监控规则模板
CREATE TABLE monitor_rules (
    rule_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    -- 条件表达式（JSON 格式）
    conditions      JSONB NOT NULL,        -- [{"type": "pe_ttm", "op": "<", "value": 15}]
    -- 触发后的动作
    actions         JSONB NOT NULL,         -- [{"type": "telegram", "chat_id": "xxx"}]
    -- 监控范围
    market          VARCHAR(10) DEFAULT 'A', -- A股/港股/ALL
    exchange        VARCHAR(10),            -- 交易所筛选
    -- 状态
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- 监控股票池（哪些股票应用哪些规则）
CREATE TABLE monitor_stock_pool (
    id          SERIAL PRIMARY KEY,
    rule_id     UUID REFERENCES monitor_rules(rule_id),
    symbol      VARCHAR(20) REFERENCES symbols(symbol),
    added_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(rule_id, symbol)
);

CREATE INDEX idx_pool_rule ON monitor_stock_pool(rule_id);
CREATE INDEX idx_pool_symbol ON monitor_stock_pool(symbol);

-- 触发事件记录
CREATE TABLE monitor_events (
    event_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id     UUID REFERENCES monitor_rules(rule_id),
    symbol      VARCHAR(20),
    trigger_time TIMESTAMP DEFAULT NOW(),
    -- 触发时的数据快照
    trigger_data JSONB,                     -- 触发时的指标值
    -- 通知状态
    notified    BOOLEAN DEFAULT FALSE,
    notified_at  TIMESTAMP,
    -- 备注
    memo        TEXT
);

CREATE INDEX idx_events_rule ON monitor_events(rule_id);
CREATE INDEX idx_events_time ON monitor_events(trigger_time DESC);
CREATE INDEX idx_events_symbol ON monitor_events(symbol);
```

---

### 6. 选股策略

```sql
-- 选股策略模板
CREATE TABLE screener_strategies (
    strategy_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         VARCHAR(100) NOT NULL,
    description  TEXT,
    -- 筛选条件
    criteria     JSONB NOT NULL,
    -- 排序方式
    sort_by      JSONB,                     -- [{"field": "roe", "direction": "desc"}]
    -- 附加条件
    market       VARCHAR(10) DEFAULT 'A',
    max_results  INTEGER DEFAULT 100,
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);

-- 历史筛选结果
CREATE TABLE screener_results (
    id          SERIAL PRIMARY KEY,
    strategy_id UUID REFERENCES screener_strategies(strategy_id),
    run_time    TIMESTAMP DEFAULT NOW(),
    results     JSONB,                      -- [{"symbol": "000001.SZ", "roe": 15.2, ...}]
    total_count INTEGER
);

CREATE INDEX idx_results_strategy ON screener_results(strategy_id);
CREATE INDEX idx_results_time ON screener_results(run_time DESC);
```

---

### 7. 回测系统

```sql
-- 策略定义
CREATE TABLE strategies (
    strategy_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(20) NOT NULL,    -- value/growth/momentum/index
    -- 策略参数
    parameters    JSONB,                   -- 策略特定参数
    -- 策略描述
    description   TEXT,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

-- 回测结果
CREATE TABLE backtest_results (
    id              SERIAL PRIMARY KEY,
    strategy_id     UUID REFERENCES strategies(strategy_id),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    -- 收益指标
    total_return    DECIMAL(10, 4),
    annual_return   DECIMAL(10, 4),
    -- 风险指标
    max_drawdown    DECIMAL(10, 4),
    volatility      DECIMAL(10, 4),
    sharpe_ratio    DECIMAL(10, 4),
    sortino_ratio   DECIMAL(10, 4),
    -- 交易统计
    total_trades    INTEGER,
    win_rate        DECIMAL(10, 4),
    avg_hold_days   INTEGER,
    -- 详细数据
    daily_returns   JSONB,                  -- 每日收益率序列
    positions       JSONB,                 -- 持仓记录
    trades          JSONB,                 -- 交易明细
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_backtest_strategy ON backtest_results(strategy_id);
CREATE INDEX idx_backtest_date ON backtest_results(start_date, end_date);
```

---

### 8. 模拟交易

```sql
-- 模拟账户
CREATE TABLE sim_accounts (
    account_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         VARCHAR(100) NOT NULL,
    initial_cash DECIMAL(20, 2) NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);

-- 持仓记录
CREATE TABLE sim_positions (
    id          SERIAL PRIMARY KEY,
    account_id  UUID REFERENCES sim_accounts(account_id),
    symbol      VARCHAR(20) NOT NULL,
    quantity    DECIMAL(20, 4) NOT NULL,    -- 股数
    avg_cost    DECIMAL(10, 4) NOT NULL,    -- 平均成本
    open_date   DATE NOT NULL,
    updated_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, symbol)
);

-- 交易记录
CREATE TABLE sim_trades (
    trade_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id  UUID REFERENCES sim_accounts(account_id),
    symbol      VARCHAR(20) NOT NULL,
    action      VARCHAR(10) NOT NULL,       -- buy/sell
    quantity    DECIMAL(20, 4) NOT NULL,
    price       DECIMAL(10, 4) NOT NULL,
    trade_date  DATE NOT NULL,
    trade_time  TIMESTAMP DEFAULT NOW(),
    commission  DECIMAL(10, 4) DEFAULT 0,
    reason      VARCHAR(100)
);

CREATE INDEX idx_trades_account ON sim_trades(account_id);
CREATE INDEX idx_trades_date ON sim_trades(trade_date);

-- 每日净值
CREATE TABLE sim_portfolio_daily (
    id          SERIAL PRIMARY KEY,
    account_id  UUID REFERENCES sim_accounts(account_id),
    trade_date  DATE NOT NULL,
    equity      DECIMAL(20, 2) NOT NULL,     -- 总权益
    cash        DECIMAL(20, 2) NOT NULL,
    position_value DECIMAL(20, 2),           -- 持仓市值
    daily_return DECIMAL(10, 4),
    UNIQUE(account_id, trade_date)
);
```

---

## 数据同步策略

### 日度同步流程

```
1. 每日收盘后（16:00后）触发同步任务
2. 同步顺序:
   a. 股票列表更新 (symbols)
   b. 日线数据 (daily_bars)
   c. 财务数据 (financial_metrics)
   d. 估值指标 (price_ratios)
3. 增量同步: 只同步最新数据，减少API调用
4. 错误重试: 失败最多重试3次，间隔5分钟
```

### 本地数据保留策略

| 数据类型 | 保留期限 |
|----------|----------|
| 日线行情 | 永久 |
| 财务数据 | 永久 |
| 监控事件 | 1年 |
| 回测结果 | 永久 |
| 模拟交易 | 永久 |

---

## Redis 缓存设计（如需）

```
监控场景:
  monitor:rules:{rule_id}     -> JSON 规则内容（TTL: 1小时）
  monitor:triggered:{symbol}:{rule_id} -> 时间戳（防重复触发，TTL: 1天）

行情缓存:
  quote:realtime:{symbol}     -> 最新行情（TTL: 60秒）
  quote:daily:{symbol}:{date} -> 日线数据缓存

性能优化:
  screener:results:{strategy_id} -> 筛选结果缓存（TTL: 4小时）
  backtest:latest               -> 最新回测结果（TTL: 30分钟）
```

---

*文档版本: v0.1*
*最后更新: 2026-05-01*