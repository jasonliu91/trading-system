# System Architecture — AI-Assisted ETH Trading System

## 1. Vision

一个以模拟盘为起点的AI辅助交易系统，最终目标是全自动化交易。系统以ETH/USDT为主要标的，在Binance上运行。

核心理念：**确定性骨架 + AI大脑 + Agent管家**。

- **确定性骨架**：数据管道、风控规则、订单执行全部用确定性代码实现
- **AI大脑 (Market Mind)**：一份持续演化的认知状态文档，赋予AI记忆、信念和自我纠偏能力。每次决策都带着累积的认知，而不是从零开始
- **Agent管家 (Overseer)**：7×24在线的Telegram Bot，是用户与系统之间的主要沟通渠道

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌──────────────────┐               ┌────────────────────────┐  │
│  │  Web UI (Next.js) │               │  Overseer Agent (管家)  │  │
│  │  K线|决策|绩效     │               │  Telegram Bot ←→ 用户   │  │
│  └────────┬─────────┘               └──────────┬─────────────┘  │
│           │ REST + WS                           │ API + LLM      │
│  ┌────────┴─────────────────────────────────────┴────────────┐  │
│  │                   Core Engine (Python)                      │  │
│  │                                                             │  │
│  │  ┌───────────────────────────────────────────────────────┐ │  │
│  │  │                 Market Mind (AI认知状态)                │ │  │
│  │  │  市场信念 | 策略偏好 | 经验教训 | 偏误警觉 | 当前关注   │ │  │
│  │  └──────────────────────┬────────────────────────────────┘ │  │
│  │                         │ 注入到每次AI调用                  │  │
│  │  ┌──────────────────────┴────────────────────────────┐    │  │
│  │  │              Orchestrator (调度器)                  │    │  │
│  │  │  定时触发分析 → 汇总信号 → 调用AI → 执行决策        │    │  │
│  │  └──┬──────────┬──────────┬──────────┬───────────────┘    │  │
│  │     │          │          │          │                     │  │
│  │  ┌──▼──┐   ┌───▼───┐  ┌──▼──┐   ┌───▼────┐              │  │
│  │  │量化  │   │新闻分析│  │AI推理│   │风控规则 │              │  │
│  │  │信号  │   │引擎   │  │引擎  │   │引擎    │              │  │
│  │  └──┬──┘   └───┬───┘  └──┬──┘   └───┬────┘              │  │
│  │     │          │          │          │                     │  │
│  │  ┌──▼──────────▼──────────▼──────────▼────┐              │  │
│  │  │        Paper Trading Engine             │              │  │
│  │  │  模拟账户 | 订单管理 | 仓位跟踪 | 绩效   │              │  │
│  │  └────────────────────────────────────────┘              │  │
│  │                                                           │  │
│  │  ┌──────────────────┐    ┌────────────────────┐          │  │
│  │  │  Data Store       │    │  Review Engine      │          │  │
│  │  │  (SQLite)         │    │  复盘 → 更新        │          │  │
│  │  │  K线|决策|交易|复盘│    │  Market Mind        │          │  │
│  │  └──────────────────┘    └────────────────────┘          │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │               Data Layer (数据采集)                         │  │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────────────┐          │  │
│  │  │Binance  │  │News APIs │  │On-chain Data    │          │  │
│  │  │REST+WS  │  │Twitter/X │  │Etherscan        │          │  │
│  │  │K线/深度  │  │CryptoPanic│ │Dune (后期)      │          │  │
│  │  └─────────┘  └──────────┘  └─────────────────┘          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│                           VPS (24/7)                             │
└──────────────────────────────────────────────────────────────────┘
```

## 3. Module Specifications

### 3.1 Market Mind (AI认知状态) — 系统的灵魂

这是整个系统最核心的创新。Market Mind是一份持续演化的结构化文档，代表AI的"认知状态"——它的市场信念、策略偏好、经验教训和自我纠偏意识。

**为什么需要它**：LLM每次调用都是无状态的。没有Market Mind，AI每次做决策就像一个从没见过的陌生分析师——给他数据让他即兴判断。有了Market Mind，AI带着累积的认知来做判断——它记得自己之前错在哪、什么信号最近靠谱、应该警惕什么偏误。

**结构定义**：

```json
{
  "version": "1.0",
  "last_updated": "2025-02-09T20:00:00Z",
  "updated_by": "weekly_review",

  "market_beliefs": {
    "regime": "trending_bullish",
    "regime_confidence": 0.7,
    "narrative": "牛市中期回调阶段，ETH/BTC汇率正在筑底，链上活跃度回升支持中期看多",
    "key_levels": {
      "support": [3000, 2800],
      "resistance": [3500, 3800]
    },
    "macro_context": "美联储暂停加息，流动性环境改善"
  },

  "strategy_weights": {
    "trend_following": {"weight": 0.7, "reason": "最近3周准确率80%"},
    "mean_reversion": {"weight": 0.3, "reason": "震荡市表现差，近期亏损"},
    "news_sentiment": {"weight": 0.4, "reason": "噪音较大，降低权重"}
  },

  "lessons_learned": [
    {"lesson": "高ADX(>30)环境下不要逆势操作", "evidence": "3次亏损验证", "added": "2025-02-02"},
    {"lesson": "资金费率连续3天>0.1%是短期见顶信号", "evidence": "2次验证", "added": "2025-02-09"},
    {"lesson": "周末流动性差，避免大仓位变动", "evidence": "滑点数据", "added": "2025-01-26"}
  ],

  "bias_awareness": [
    {"bias": "用户对ETH有长期看多倾向，可能导致忽视看空信号", "mitigation": "看多决策需要至少2个独立信号确认"},
    {"bias": "连续盈利后容易过度自信放大仓位", "mitigation": "连续盈利3次后仓位上限自动降低到15%"},
    {"bias": "大跌时倾向于'抄底'", "mitigation": "回测显示等趋势确认再入场胜率更高，禁止在下跌趋势中逆势买入"}
  ],

  "active_watchlist": [
    {"item": "$3500阻力位", "action": "突破且日线收盘站稳则加仓", "deadline": null},
    {"item": "ETH/BTC汇率0.04", "action": "站上则ETH跑赢BTC趋势确认", "deadline": null},
    {"item": "下周FOMC会议", "action": "会议前减仓至50%以下敞口", "deadline": "2025-02-19"}
  ],

  "user_inputs": [
    {"input": "用户认为美联储今年会降息2次，对ETH中期利好", "date": "2025-02-10", "incorporated": true}
  ],

  "performance_memory": {
    "recent_accuracy": {"last_10_decisions": 0.6, "trend": "improving"},
    "worst_pattern": "在震荡市中频繁交易，小亏累积",
    "best_pattern": "在强趋势中持有，单次大盈利"
  }
}
```

**生命周期**：

```
Phase 1: 手动初始化
  用户（你）写一个初始版本，包含你的市场信念和已知偏误
  → 注入到AI决策prompt中
  → AI决策时参考这些认知

Phase 1-3: 手动 + 半自动更新
  每周你review AI的决策，手动更新Market Mind
  → 也可以通过Telegram告诉Agent你的新观点
  → Agent写入user_inputs

Phase 4: 自动更新
  复盘引擎自动分析决策记录
  → 更新strategy_weights（基于近期准确率）
  → 添加新的lessons_learned（基于重复出现的失败模式）
  → 更新market_beliefs（基于市场结构变化）
  → 生成更新理由，供你review
```

**在AI决策中的注入方式**：

Market Mind作为system prompt的核心部分注入到每次AI决策调用中：

```
[System Prompt]
你是ETH量化交易分析师。

## 你的当前认知状态 (Market Mind)
{market_mind_json}

## 重要提醒
- 你的偏误警觉列表中有{n}条提醒，做决策前请检查
- 上次更新认知是在{days}天前
- 你最近10次决策的准确率是{accuracy}

## 任务
基于以下市场数据，结合你的认知状态，给出交易建议...
```

### 3.2 Data Layer (数据层)

职责：从外部数据源采集数据，标准化格式后存储。

| 数据源 | 数据类型 | 频率 | 优先级 |
|--------|---------|------|--------|
| Binance REST API | 历史K线 (1h, 4h, 1d) | 启动时拉取 | P0 |
| Binance WebSocket | 实时价格, K线更新 | 实时 | P0 |
| Binance REST API | 资金费率, 深度数据 | 每小时 | P1 |
| CryptoPanic / NewsAPI | 加密货币新闻 | 每15分钟 | P2 |
| Twitter/X API | KOL发言 | 每15分钟 | P2 |
| Etherscan API | 大额转账, Gas, ETH供应 | 每小时 | P2 |

标准化输出格式：
```json
{
  "source": "binance_kline",
  "symbol": "ETHUSDT",
  "timestamp": "2025-01-01T00:00:00Z",
  "data_type": "kline_1d",
  "payload": { ... },
  "received_at": "2025-01-01T00:00:01Z"
}
```

### 3.3 Quant Signal Engine (量化信号引擎)

职责：基于技术指标计算交易信号。纯确定性代码，无AI介入。

已验证的策略（来自历史回测）：
- EMA + ADX (日线级别)
- Supertrend (日线级别)
- Donchian Channel Breakout (日线级别)

关键发现：日线(1d)策略显著优于小时(1h)和4小时(4h)策略。

信号输出格式：
```json
{
  "strategy_name": "ema_adx_daily",
  "symbol": "ETHUSDT",
  "timeframe": "1d",
  "timestamp": "2025-01-01T00:00:00Z",
  "signal": "buy",
  "strength": 0.75,
  "indicators": {
    "ema_fast": 3200.5,
    "ema_slow": 3100.2,
    "adx": 28.5
  },
  "reasoning": "EMA金叉 + ADX > 25确认趋势强度"
}
```

### 3.4 News Analysis Engine (新闻分析引擎)

职责：处理非结构化信息源，输出结构化的情绪和事件信号。Phase 3加入。

信号输出格式：
```json
{
  "source": "twitter_kol",
  "timestamp": "2025-01-01T12:00:00Z",
  "sentiment": "bullish",
  "confidence": 0.6,
  "key_events": ["ETH ETF资金流入创新高"],
  "summary": "多数KOL看多，主要基于ETF资金流数据"
}
```

### 3.5 AI Reasoning Engine (AI推理引擎)

职责：综合Market Mind认知状态 + 所有信号源，做出交易决策。

**输入**：Market Mind + 量化信号 + 新闻情绪 + 当前持仓 + 最近N次决策记录
**输出**：结构化的交易决策

关键设计原则：
- 每次调用都带有Market Mind作为认知上下文
- 输出必须是结构化JSON
- 推理过程必须包含：参考了Market Mind中的哪些认知、检查了哪些偏误提醒

决策输出格式：
```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "decision": "buy",
  "position_size_pct": 15,
  "entry_price": 3250.0,
  "stop_loss": 3100.0,
  "take_profit": 3500.0,
  "confidence": 0.7,
  "reasoning": {
    "market_regime": "trending_bullish",
    "mind_alignment": "与Market Mind的牛市中期判断一致",
    "quant_signals_summary": "2/3策略看多",
    "news_sentiment": "中性偏多",
    "key_factors": ["日线EMA金叉", "ADX趋势确认", "资金费率正常"],
    "risk_considerations": ["接近前高阻力位", "4h级别有超买迹象"],
    "bias_check": "检查偏误#1(ETH过度乐观): 本次有2个独立信号确认，通过",
    "final_logic": "多数信号一致看多，趋势确认，但考虑阻力位控制仓位在15%"
  },
  "model_used": "claude-sonnet-4-5-20250929",
  "input_hash": "abc123..."
}
```

### 3.6 Risk Management Engine (风控规则引擎)

职责：对AI的决策进行硬性规则检查。纯确定性代码。

规则（可配置）：
- 单笔最大仓位：总资金的 20%
- 总敞口上限：总资金的 60%
- 单日最大亏损：总资金的 5%（触发后当日停止交易）
- 止损必须设置，最大亏损不超过入场价的 8%
- 连续亏损 3 次后，仓位减半直到盈利一次
- Market Mind中的bias_awareness可以动态添加规则（如"连续盈利3次后上限降到15%"）

### 3.7 Paper Trading Engine (模拟交易引擎)

职责：模拟订单执行，跟踪仓位和资金。

核心数据：
- 账户余额（初始 10,000 USDT）
- 当前持仓（数量、均价、未实现盈亏）
- 历史交易记录
- 绩效指标（总收益率、最大回撤、胜率、盈亏比、Sharpe等）

### 3.8 Review Engine (复盘引擎)

职责：定期分析历史决策，更新Market Mind。

触发频率：每周一次自动复盘 + 可手动触发
输入：过去一周/一月的所有决策记录 + 实际结果 + 当前Market Mind
输出：
1. 复盘报告（存入数据库，显示在UI上，通过Agent发送）
2. **Market Mind更新建议**（新的lessons、调整后的weights、更新的beliefs）

Phase 4完善自动更新。Phase 1-3期间手动更新Market Mind。

### 3.9 Orchestrator (调度器)

定时任务：
- 每1小时：拉取最新K线 → 计算量化信号
- 每4小时（或每天）：加载Market Mind → 触发AI分析 → 风控检查 → 模拟执行
- 每15分钟：拉取新闻数据（Phase 3）
- 每周日：触发复盘 → 更新Market Mind（Phase 4自动，之前手动）

### 3.10 Web UI (Dashboard)

技术选型：Next.js + TypeScript + Tailwind CSS + TradingView Lightweight Charts

页面结构：
- **主看板 `/`**：ETH K线图 + 当前持仓 + 最新AI决策 + 账户概览
- **决策历史 `/decisions`**：决策列表，展开看推理过程（含Market Mind引用）
- **Market Mind `/mind`**：展示AI当前认知状态，可手动编辑（Phase 1）
- **信号面板 `/signals`**：各策略信号的实时状态
- **复盘报告 `/review`**：AI的周度复盘 + Market Mind变更历史
- **绩效统计 `/performance`**：资金曲线、关键指标
- **系统状态 `/system`**：模块运行状态、配置管理

### 3.11 Overseer Agent (管家Agent)

职责：7×24在线Telegram Bot，感知系统全部状态（含Market Mind），与用户沟通。

**主动通知**：新决策、止损止盈触发、系统异常、每日日报、每周周报
**被动响应**：查仓位、查绩效、问"为什么买入了"、问"你现在怎么看市场"
**指令执行**：触发分析、暂停/恢复交易
**Market Mind交互**：
- 用户说"我觉得下周会降息" → Agent写入Market Mind的user_inputs
- 用户问"你现在怎么看市场" → Agent读取Market Mind的market_beliefs回答
- 用户说"你最近太保守了" → Agent记录偏好，但同时引用bias_awareness提醒用户

**LLM使用策略**：
- 简单查询（关键词匹配）：直接格式化数据，不调用LLM
- 复杂查询：调用Claude Haiku/GPT-4o-mini（快且便宜）
- 涉及Market Mind分析的深度对话：调用Claude Sonnet

## 4. Tech Stack

```
┌───────────────────────┐  ┌───────────────────────────────────┐
│  Frontend (Next.js)   │  │  Backend (Python)                 │
│                       │  │                                    │
│  Next.js 14+          │  │  FastAPI + uvicorn                │
│  TypeScript           │◄►│  python-binance                   │
│  Tailwind CSS         │  │  anthropic / openai SDK           │
│  shadcn/ui            │  │  pandas, ta                       │
│  TradingView LW Charts│  │  SQLAlchemy + SQLite              │
│  Zustand              │  │  APScheduler                      │
│                       │  │                                    │
│  Port: 3000           │  │  Port: 8000                       │
└───────────────────────┘  └──────────────┬────────────────────┘
                                          │ 同一套API
                           ┌──────────────▼────────────────────┐
                           │  Overseer Agent (Python)           │
                           │  python-telegram-bot               │
                           │  anthropic / openai SDK            │
                           │  独立进程                           │
                           └────────────────────────────────────┘
```

| 组件 | 技术选择 |
|------|---------|
| 前端框架 | Next.js 14+ (TypeScript) |
| 样式 | Tailwind CSS + shadcn/ui |
| K线图表 | TradingView Lightweight Charts |
| 前端状态 | Zustand |
| 后端框架 | FastAPI |
| 后端语言 | Python 3.11+ |
| 数据库 | SQLite + SQLAlchemy |
| 交易所API | python-binance |
| AI | Anthropic API (Claude) + OpenAI API (GPT) |
| 即时通讯 | Telegram Bot (python-telegram-bot) |
| 定时任务 | APScheduler |
| 版本控制 | Git |

### API路由

```
# 数据查询
GET    /api/klines?timeframe=1d&limit=90
GET    /api/portfolio
GET    /api/decisions?page=1&limit=20
GET    /api/decisions/{id}
GET    /api/performance
GET    /api/signals

# Market Mind
GET    /api/mind                              # 读取当前Market Mind
PUT    /api/mind                              # 更新Market Mind
GET    /api/mind/history                      # Market Mind变更历史

# 系统管理
GET    /api/system/status
GET    /api/system/health
POST   /api/system/trigger-analysis
POST   /api/system/pause
POST   /api/system/resume
POST   /api/config/update

# Agent专用
GET    /api/summary/daily
GET    /api/summary/weekly

# 实时推送
WS     /ws/live
```

## 5. Data Flow — 单次决策周期

```
1.  Scheduler 触发 "分析周期"
2.  Data Layer 拉取最新K线和市场数据
3.  Quant Engine 计算各策略信号
4.  (Phase 3+) News Engine 获取最新新闻情绪
5.  Market Mind 加载当前认知状态
6.  Orchestrator 打包: 信号 + Market Mind + 持仓 + 历史决策 → 构造AI输入
7.  AI Engine 调用LLM → 返回结构化决策（含对Market Mind的引用和偏误检查）
8.  Risk Engine 检查决策是否符合风控规则（含Market Mind中的动态规则）→ 调整或否决
9.  Paper Trading Engine 执行模拟交易 → 更新仓位
10. 所有数据写入SQLite
11. WebSocket 推送更新 → Web UI 刷新
12. Overseer Agent 收到通知 → 通过Telegram发送决策摘要给用户
```

## 6. Learning Loop — Market Mind的演化

```
做决策（带着认知）→ 看结果 → 复盘分析 → 更新认知 → 做更好的决策
     ▲                                              │
     └──────────────────────────────────────────────┘
```

这是系统最核心的价值：不只是执行策略，而是持续学习和自我修正。

## 7. Phased Development Plan

| Phase | 时间 | 内容 | Market Mind状态 |
|-------|------|------|----------------|
| 1 | 第1-5周 | K线 + AI决策 + 模拟交易 + Web UI + Telegram Agent | 手动初始化和维护 |
| 2 | 第6-9周 | 量化信号引擎 + 回测 | 手动更新strategy_weights |
| 3 | 第10-13周 | 新闻/链上数据接入 | 手动更新 + Agent接收用户输入 |
| 4 | 第14-17周 | AI复盘与自动Market Mind更新 | 自动演化 |
| 5 | 待定 | 实盘接入 | 完全自动 |

## 8. Deployment — 三个进程

```bash
# 进程1: Python后端
uvicorn backend.src.api.main:app --host 0.0.0.0 --port 8000

# 进程2: Next.js前端
cd frontend && npm start  # 端口3000，nginx反向代理

# 进程3: Overseer Agent
python -m backend.src.agent.main
```

## 9. Key Design Decisions

详见 docs/DECISIONS.md
