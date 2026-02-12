# PRD: Phase 1 — 最小可用模拟交易系统

## 概述

Phase 1 交付：网页Dashboard（K线+AI决策）+ Telegram Bot（随时沟通）+ Market Mind（AI认知状态）+ 模拟交易。

用户可以通过Telegram随时了解系统状态，通过网页看详细数据，通过Market Mind页面查看和编辑AI的"思维方式"。

## 用户故事

1. 我打开Dashboard能看到专业ETH K线图和当前价格
2. AI每4小时自动做决策，我能看到完整推理过程——包括它参考了Market Mind中的哪些认知
3. 模拟账户正确跟踪盈亏
4. 我能查看和编辑Market Mind，调整AI的市场信念和偏误警觉
5. AI做了新决策时我在Telegram收到通知
6. 我随时可以在Telegram问"现在仓位怎样"、"你怎么看市场"
7. 我可以通过Telegram告诉AI我的市场观点，它会记录到Market Mind
8. 一切自动运行，我不需要手动触发

## 功能规格

### F1: 数据采集
- Binance ETH/USDT K线: 1h, 4h, 1d
- 历史拉取: 90天1d + 7天1h/4h
- 实时更新: Binance WebSocket
- 额外: 当前价格、24h成交量和涨跌幅

### F2: 技术指标
- MA(20, 50, 200), RSI(14), MACD(12,26,9), ATR(14), 布林带(20,2)
- Phase 1只提供原始值给AI，不做信号判断

### F3: Market Mind
- **初始化**: 提供JSON模板，用户手动填写初始认知（市场信念、已知偏误等）
- **注入**: 每次AI决策时作为system prompt核心部分
- **Web编辑**: `/mind` 页面可查看和手动修改各板块
- **Agent输入**: 用户通过Telegram发送观点 → 写入user_inputs
- **版本管理**: 每次修改记录到history表，可查看变更历史
- Phase 1为手动维护，Phase 4升级为自动更新

### F4: AI交易决策
- 频率: 每4小时（可配置）
- 输入: Market Mind + 30根日线K线+指标 + 24根小时K线 + 持仓 + 最近5次决策
- Prompt包含: Market Mind注入 + 偏误检查提醒 + 结构化输出要求
- 输出: 结构化JSON（含mind_alignment和bias_check字段）
- 模型: Claude Sonnet 4.5（默认），可配置

### F5: 风控规则
| 规则 | 阈值 | 动作 |
|------|------|------|
| 单笔最大仓位 | 20% | 自动调整 |
| 总敞口上限 | 60% | 拒绝开仓 |
| 必须止损 | - | 拒绝无止损决策 |
| 止损距离上限 | 8% | 自动调整 |
| 单日最大亏损 | 5% | 当日停止交易 |
| Market Mind动态规则 | 读取bias_awareness | 如"连续盈利3次后仓位降到15%" |

### F6: 模拟交易
- 初始10,000 USDT，手续费0.1%，滑点0.05%
- 支持: 市价买卖、止损/止盈触发

### F7: Web Dashboard
- **主看板 `/`**: TradingView K线(1h/4h/1d) + MA + 买卖标注 | 价格/账户/持仓/最新决策
- **Market Mind `/mind`**: 展示+编辑AI认知状态，变更历史
- **决策历史 `/decisions`**: 列表+展开推理过程（含Mind引用和偏误检查）
- **绩效 `/performance`**: 资金曲线 + 指标卡片
- **系统 `/system`**: 模块状态、手动触发、配置
- UI规范: 暗色主题、绿涨红跌、桌面优先

### F8: Overseer Agent (Telegram Bot)
**主动通知**: 新决策(含推理摘要)、止损止盈、系统异常、每日日报
**被动响应**: 查仓位、查绩效、问"为什么买入了"、问"你怎么看市场"(读Market Mind)
**Market Mind交互**: 用户发送市场观点 → 写入user_inputs → 确认
**指令执行**: 触发分析、暂停/恢复交易（带确认）
**LLM策略**: 简单查询直接返回，复杂查询用Haiku/4o-mini，深度对话用Sonnet

### F9: 配置
```python
TRADING_PAIR = "ETHUSDT"
ANALYSIS_INTERVAL_HOURS = 4
INITIAL_BALANCE = 10000
MAX_POSITION_PCT = 0.20
MAX_EXPOSURE_PCT = 0.60
MAX_DAILY_LOSS_PCT = 0.05
MAX_STOP_LOSS_PCT = 0.08
TRADING_FEE_PCT = 0.001
SLIPPAGE_PCT = 0.0005
AI_MODEL = "claude-sonnet-4-5-20250929"
TELEGRAM_BOT_TOKEN = ""  # 环境变量
TELEGRAM_CHAT_ID = ""    # 环境变量
```

## 验收标准

1. 网页有专业K线图，支持时间框架切换
2. AI每4小时自动决策，输出包含Market Mind引用和偏误检查
3. 模拟账户正确跟踪盈亏
4. Market Mind页面可查看和编辑，变更有历史记录
5. 决策历史可查看，推理详情含Mind alignment
6. 绩效页面有资金曲线和指标
7. Telegram Bot在线：能查状态、收通知、发观点、执行指令
8. 三进程VPS部署稳定运行48小时+

## 不包含

- 量化策略信号（Phase 2）
- 新闻/链上数据（Phase 3）
- Market Mind自动更新（Phase 4）
- 实盘交易（Phase 5）
