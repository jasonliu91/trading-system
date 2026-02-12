# AGENTS.md — OpenAI Codex 项目上下文

> 先阅读本文件，再阅读 docs/ 下文档。

## 项目

AI辅助ETH/USDT模拟交易系统: Python后端(FastAPI) + Next.js前端 + Telegram Bot(Overseer Agent)。核心概念是 **Market Mind**——AI的持续认知状态。

## 文档

- `docs/ARCHITECTURE.md` — 架构（必读，含Market Mind设计）
- `docs/PRD_PHASE1.md` — Phase 1需求
- `docs/TASK_QUEUE.md` — 任务
- `docs/DECISIONS.md` — 决策
- `docs/CURRENT_STATUS.md` — 进度

## 技术栈

- 后端: Python 3.11+, FastAPI, SQLAlchemy, APScheduler, python-binance, anthropic, python-telegram-bot
- 前端: Next.js 14+, TypeScript, Tailwind CSS, shadcn/ui, TradingView Lightweight Charts, Zustand

## 目录

```
backend/src/ → api/, data/, quant/, ai/, mind/, risk/, trading/, db/, orchestrator/, agent/, config.py
frontend/src/ → app/, components/, lib/, hooks/, stores/
```

## 关键约束

- AI决策是单次结构化调用（注入Market Mind）
- 决策输出必须含mind_alignment和bias_check
- 风控规则硬性执行
- Overseer Agent不做交易决策
- 前端和Agent共用同一套后端API
- Market Mind变更必须有history记录

## Session结束前

1. git commit
2. 更新 docs/CURRENT_STATUS.md
3. 设计决策 → docs/DECISIONS.md
