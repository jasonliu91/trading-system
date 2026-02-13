# Task Queue

每个任务设计为一个开发session（30-90分钟）可完成。完成后打 [x] 并记录日期。

---

## Phase 0: 项目初始化

### [x] T001: 初始化Git仓库（2026-02-12）
**P0** | 15分钟 | 初始化Git，配置.gitignore

### [x] T002: Python后端环境配置（2026-02-12）
**P0** | 30分钟 | backend/下创建venv，安装依赖: python-binance, fastapi, uvicorn, anthropic, openai, pandas, ta, sqlalchemy, python-dotenv, apscheduler, websockets, python-telegram-bot

### [x] T003: Next.js前端初始化（2026-02-12）
**P0** | 30分钟 | `npx create-next-app@latest frontend --typescript --tailwind --app --use-npm`，安装lightweight-charts, zustand, shadcn/ui

### [x] T004: 项目目录结构（2026-02-12）
**P0** | 20分钟 | 创建完整目录结构:
```
backend/src/ → data/, quant/, ai/, risk/, trading/, db/, orchestrator/, api/, agent/, mind/
frontend/src/ → app/, components/, lib/, hooks/, stores/
```

### T005: 整理OpenClaw现有代码
**P1** | 60分钟 | 将OpenClaw市场分析代码迁移到新项目

---

## Phase 1: 最小可用系统

### 后端核心

### [x] T006: FastAPI骨架 + 全部API路由（mock数据）（2026-02-12）
**P0** | 60分钟 | 包含Market Mind的API路由（GET/PUT /api/mind）

### [x] T007: SQLite数据库初始化（2026-02-12）
**P0** | 45分钟 | 表: klines, decisions, trades, performance, market_mind_history

### [x] T008: Binance K线数据拉取（2026-02-12）
**P0** | 60分钟 | ETH/USDT 1h/4h/1d，存入SQLite，通过API提供

### [x] T009: Market Mind初始化模块（2026-02-12）
**P0** | 60分钟 | 实现market_mind.py: load(), save(), inject_to_prompt(), update()。创建初始Market Mind JSON文件（你手动填写内容，代码提供框架）。Market Mind变更记录到history表。

### [x] T010: AI决策模块（集成Market Mind）（2026-02-12）
**P0** | 90分钟 | 构造prompt时注入Market Mind。AI输出需包含mind_alignment和bias_check字段。

### [x] T011: 模拟交易引擎（2026-02-12）
**P0** | 60分钟 | 纸盘交易：开仓、平仓、仓位跟踪、盈亏计算（含手续费滑点）

### [x] T012: 风控规则引擎（2026-02-12）
**P0** | 45分钟 | 硬性规则检查 + 支持从Market Mind读取动态规则（如bias_awareness中的仓位限制）

### [x] T013: 调度器（2026-02-12）
**P0** | 60分钟 | APScheduler定时任务：拉数据→计算指标→加载Mind→AI决策→风控→模拟执行

### 前端

### [x] T014: 主看板 — K线图表（2026-02-12）
**P0** | 90分钟 | TradingView Lightweight Charts，1h/4h/1d切换，MA线，买卖点标注

### [x] T015: 主看板 — 信息面板（2026-02-12）
**P0** | 60分钟 | 当前价格、账户概览、持仓卡片、最新AI决策卡片。暗色主题。

### T016: Market Mind页面
**P1** | 90分钟 | `/mind` 页面：展示当前Market Mind各板块（市场信念、策略偏好、经验教训、偏误警觉），支持手动编辑并保存。显示变更历史。

### T017: 决策历史页面
**P1** | 90分钟 | `/decisions` 展示决策列表，展开看推理过程（含Market Mind引用和偏误检查结果）

### T018: 绩效页面
**P1** | 60分钟 | `/performance` 资金曲线 + 关键指标卡片

### T019: WebSocket实时推送
**P1** | 60分钟 | 后端推送实时价格和新决策，前端接收并更新

### Overseer Agent

### T020: Telegram Bot基础搭建
**P0** | 60分钟 | 创建Bot（@BotFather），实现消息收发，连接后端API
**前置**: 需先通过@BotFather创建Bot并获取Token

### T021: Agent状态查询
**P0** | 60分钟 | 用户可问"持仓"/"绩效"/"最新决策"/"系统状态"/"你怎么看市场"（读取Market Mind）

### T022: Agent主动通知
**P1** | 60分钟 | 新决策/止损止盈/系统异常/每日日报 → Telegram推送

### T023: Agent接收用户输入到Market Mind
**P1** | 45分钟 | 用户说市场观点 → Agent写入Market Mind的user_inputs → 确认回复

### T024: Agent指令执行
**P2** | 45分钟 | "触发分析"/"暂停交易"/"恢复交易"（带确认）

### 部署

### T025: VPS部署
**P1** | 90分钟 | 三个进程 + supervisor/systemd + nginx反向代理

---

## Phase 2-4: 待Phase 1完成后细化

- Phase 2: 量化信号引擎 + 回测 + 策略信号写入Market Mind权重
- Phase 3: 新闻/链上数据接入 + Agent接收用户观点
- Phase 4: 复盘引擎自动更新Market Mind（lessons, weights, beliefs）
