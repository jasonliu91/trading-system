# CLAUDE.md — Claude Code 项目上下文

> 每次session开始时，先阅读本文件，再阅读 docs/ 下相关文档。

## 项目简介

AI辅助ETH/USDT模拟交易系统，三部分：
1. **Python后端** (FastAPI): 数据采集、AI决策、模拟交易、风控、Market Mind管理
2. **Next.js前端** (Dashboard): K线图表、决策展示、Market Mind编辑、绩效统计
3. **Overseer Agent** (Telegram Bot): 7×24在线，状态感知，与用户沟通

**核心概念: Market Mind** — AI的认知状态文档，注入到每次决策调用中。详见 `docs/ARCHITECTURE.md` 的 3.1 节。

## 文档索引

- `docs/ARCHITECTURE.md` — 系统架构（必读）
- `docs/PRD_PHASE1.md` — Phase 1需求
- `docs/TASK_QUEUE.md` — 待开发任务
- `docs/DECISIONS.md` — 设计决策
- `docs/CURRENT_STATUS.md` — 进度
- `docs/market_mind_init.json` — Market Mind初始模板

## 目录结构

```
backend/src/
├── api/            # FastAPI路由
├── data/           # 数据采集 (Binance)
├── quant/          # 量化信号
├── ai/             # AI推理
├── mind/           # Market Mind管理
├── risk/           # 风控
├── trading/        # 模拟交易
├── db/             # 数据库
├── orchestrator/   # 调度器
├── agent/          # Telegram Bot
└── config.py

frontend/src/
├── app/            # Next.js页面
├── components/     # React组件
├── lib/            # API client
├── hooks/          # 自定义hooks
└── stores/         # Zustand
```

## 开发规范

- **后端 Python**: docstring(中文), type hints, try/except
- **前端 TypeScript**: JSDoc, interface定义Props, 避免any
- **Git**: 每个小功能commit, 格式 `[模块] 描述`
- **API keys**: 环境变量, 不硬编码
- **Market Mind**: 变更必须记录到history表
- **AI决策输出**: 必须包含mind_alignment和bias_check字段
- **风控规则是硬性的**: AI决策必须过风控

## 常用命令

```bash
cd backend && uvicorn src.api.main:app --reload --port 8000
cd frontend && npm run dev
cd backend && python -m src.agent.main
cd backend && python -m pytest tests/
```

## Session结束前

1. git commit所有改动
2. 更新 docs/CURRENT_STATUS.md
3. 设计决策记录到 docs/DECISIONS.md
