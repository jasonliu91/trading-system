# ETH AI Trading System

AI辅助ETH/USDT模拟交易系统。**确定性骨架 + AI大脑(Market Mind) + Agent管家**。

## 系统组成

- **Python后端**: 数据采集、AI决策、模拟交易、风控、Market Mind (FastAPI, port 8000)
- **Next.js前端**: K线图表、决策展示、Market Mind编辑、绩效 (port 3000)
- **Overseer Agent**: Telegram Bot，7×24在线，感知系统状态，与用户沟通

## 核心概念: Market Mind

Market Mind是AI的认知状态文档——市场信念、策略偏好、经验教训、偏误警觉。它注入到每次AI决策调用中，让AI带着累积的认知做判断而非从零开始。详见 `docs/ARCHITECTURE.md`。

## 文档

| 文档 | 内容 |
|------|------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构（含Market Mind完整设计） |
| [docs/PRD_PHASE1.md](docs/PRD_PHASE1.md) | Phase 1需求 |
| [docs/TASK_QUEUE.md](docs/TASK_QUEUE.md) | 25个开发任务 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | 10+ 设计决策 |
| [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md) | 当前进度 |
| [docs/market_mind_init.json](docs/market_mind_init.json) | Market Mind初始模板 |

## AI工具入口

Claude Code → `CLAUDE.md` | OpenAI Codex → `AGENTS.md` | 其他 → 本文件 + `docs/`

## 启动

```bash
# 后端
cd backend && ./scripts/setup_venv.sh
cd ..
PYTHONPATH=$(pwd) backend/.venv/bin/uvicorn backend.src.api.main:app --port 8000

# 前端
cd frontend && npm install && npm run dev

# Agent
cd ..
PYTHONPATH=$(pwd) backend/.venv/bin/python -m backend.src.agent.main
```

## 本地三进程脚本

```bash
./scripts/dev_start.sh          # 启动 backend + frontend
START_AGENT=true ./scripts/dev_start.sh
VENV_DIR=/path/to/backend/.venv310 ./scripts/dev_start.sh
./scripts/dev_status.sh
./scripts/dev_stop.sh
```

## 当前可用页面

- `/` Dashboard（K线 + 持仓 + 最新决策 + WS实时价格）
- `/mind` Market Mind（展示、JSON编辑、历史）
- `/decisions` 决策历史（展开查看推理和偏误检查）
- `/performance` 绩效页（资金曲线 + 指标）

## 部署模板

- systemd/nginx/安装脚本位于 `deploy/`
- 入口文档：`deploy/README.md`

## 阶段

| Phase | 内容 | Market Mind |
|-------|------|-------------|
| 1 (当前) | K线+AI决策+模拟交易+Web UI+Telegram Agent | 手动维护 |
| 2 | 量化信号+回测 | 手动更新权重 |
| 3 | 新闻/链上数据 | Agent接收用户输入 |
| 4 | AI复盘+自动改进 | 自动演化 |
| 5 | 实盘接入 | 完全自动 |
