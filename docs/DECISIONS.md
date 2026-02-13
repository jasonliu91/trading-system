# Design Decisions Log

新决策添加在最前面。

---

## D022: 前端开发模式加入缓存损坏恢复与弱结构数据防御
**日期**: 2026-02-13
**决策**: 当 Next.js 开发模式出现 `.next/server` chunk 缺失（如 `Cannot find module './24.js'`）时，采用“停止服务 -> 清理 `frontend/.next` -> 重启 dev”作为标准恢复步骤；同时 `/mind` 页面对 `strategy_weights/lessons_learned/bias_awareness` 做类型归一化，避免手工编辑后的弱结构数据触发前端崩溃
**原因**:
- 本地 HMR 过程中可能出现缓存不一致，直接导致首页 500
- Market Mind 支持手工 JSON 编辑，数据形态不稳定时需要前端容错
- 保持调试链路可快速自愈，避免误判为后端或业务逻辑故障
**关键约束**:
- 该恢复步骤仅用于开发环境，不作为生产故障处理方案
- 容错只做展示层兜底，不替代后端 schema 约束

## D021: 本地运行基线统一为仓库内独立路径
**日期**: 2026-02-13
**决策**: 本地与部署启动统一使用 `PYTHONPATH=<repo-root>` + `backend.src.*` 模块路径；`dev_start.sh` 增加 `VENV_DIR` 覆盖并优先使用 `backend/.venv310`；`setup_venv.sh` 强制 Python >= 3.10
**原因**:
- 避免 `src.*` 相对路径在不同工作目录下导入失败
- 修复 Python 3.9 环境下类型语法兼容问题，保证后端稳定启动
- 当前环境未安装 OpenClaw，运行链路保持与 OpenClaw 迁移解耦
**关键约束**:
- 生产与本地命令均以仓库根目录为 `PYTHONPATH`
- 不引入 OpenClaw 迁移前置步骤，保持系统可独立运行

## D020: 本地联调采用脚本化三进程管理
**日期**: 2026-02-12
**决策**: 提供 `scripts/dev_start.sh`、`scripts/dev_stop.sh`、`scripts/dev_status.sh` 管理 backend/frontend/agent 本地进程
**原因**:
- 降低本地联调启动成本，避免手工开多个终端
- 统一日志路径（`.run/*.log`）便于故障定位
- Agent默认不启动，避免无Token时报错影响主流程
**关键约束**:
- 仅用于开发环境，不替代 VPS systemd 部署
- `START_AGENT=true` 且配置有效时才启动 Agent

## D019: 部署脚本支持 dry-run 预演模式
**日期**: 2026-02-12
**决策**: `install_services.sh` 与 `full_deploy.sh` 增加 `DRY_RUN=true` 模式，仅打印关键命令不执行系统变更
**原因**:
- 首次部署前可先验证变量与路径替换结果
- 降低误操作风险，便于运维审核
- 在本地非 Linux 环境也能完成流程演练
**关键约束**:
- dry-run 不做服务重启与健康检查
- 上线执行前必须至少跑一次非 dry-run

## D018: 部署流程采用“可组合脚本 + 一键入口”双模式
**日期**: 2026-02-12
**决策**: 保留 `preflight/install/post_check` 可组合脚本，同时提供 `full_deploy.sh` 一键执行入口
**原因**:
- 一键入口降低首次部署门槛
- 可组合脚本便于故障场景下分步重试
- 适合不同团队协作方式（运维与开发都可用）
**关键约束**:
- 一键部署依赖目标机具备网络与 sudo 权限
- 若需要离线部署，必须使用分步模式并跳过对应阶段

## D017: 部署配置采用“模板 + 渲染”方式注入环境差异
**日期**: 2026-02-12
**决策**: 保留仓库内统一模板（systemd/nginx），通过 `render_configs.sh` 在部署时按 `PROJECT_DIR/DEPLOY_USER/PUBLIC_DOMAIN` 等变量渲染后再安装
**原因**:
- 避免在仓库提交机器特定路径和域名
- 降低多环境部署时手改配置出错概率
- 与 `preflight/post_deploy_check` 形成可重复的部署流程闭环
**关键约束**:
- 模板文件必须保持默认占位值，避免直接改成某台机器专用配置
- 渲染产物放在 `deploy/.rendered`，不纳入版本控制

## D016: OpenClaw迁移任务标记为环境不适用（N/A）
**日期**: 2026-02-12
**决策**: 在当前仓库与本机项目目录未发现 OpenClaw 代码源，`T005` 标记为 N/A，不再阻塞 Phase 1 交付
**原因**:
- 迁移任务前置条件（存在可迁移代码）不满足
- 继续等待会阻塞系统功能和部署推进
- 当前系统已可独立运行，不依赖 OpenClaw 组件
**关键约束**:
- 若后续补充 OpenClaw 源码，再单独开迁移任务，不覆盖现有模块

## D015: 部署采用“仓库模板化 + VPS最小执行步骤”策略
**日期**: 2026-02-12
**决策**: 将 systemd 服务文件、nginx 配置和安装脚本纳入 `deploy/`，在 VPS 仅执行最少命令完成部署
**原因**:
- 降低手工部署错误率，方便复用与回滚
- 部署配置与代码版本绑定，便于审计和团队协作
- 满足三进程架构（backend/frontend/agent）的统一运维入口
**关键约束**:
- 服务路径和域名必须在目标环境中显式替换
- 部署脚本只负责安装与重载，不包含密钥写入

## D014: Agent危险操作采用“确认执行”与定时通知机制
**日期**: 2026-02-12
**决策**: 对 `trigger-analysis/pause/resume` 采用二次确认（`/confirm` `/cancel`）执行；Agent通过定时任务主动推送新决策、交易事件、系统健康异常与每日日报
**原因**:
- 避免误触发造成系统状态变化
- 用户不盯盘时仍能第一时间获取关键事件
- 与“Agent不直接做决策，只做管家与通知”定位一致
**关键约束**:
- 所有执行动作必须走后端API，不在Agent侧实现业务逻辑
- 通知逻辑需要可关闭（无 `TELEGRAM_CHAT_ID` 时不发送）

## D013: Overseer Agent 采用“命令优先 + 关键词回退”交互策略
**日期**: 2026-02-12
**决策**: Telegram Agent优先支持显式命令（/status /portfolio /performance /decision /mind /analyze /pause /resume /view），同时对中文关键词做回退识别；用户观点写入 `MarketMind.user_inputs`
**原因**:
- 命令路径最稳定，便于故障排查和自动化
- 关键词回退提升自然对话可用性，符合PRD中的“随时问”场景
- 用户观点先入库到 `user_inputs`，保持审计轨迹和后续人工/自动纳入流程
**关键约束**:
- Agent不直接做交易决策，仅调后端API获取结果或触发分析
- 写入Market Mind必须通过后端API并保留 `change_summary`

## D012: 前端页面采用“多页拆分 + 统一API层 + WS增强”的实现
**日期**: 2026-02-12
**决策**: 将 Phase 1 Web 拆分为 `/`、`/mind`、`/decisions`、`/performance` 四个页面，统一通过 `frontend/src/lib/api.ts` 调用后端，并在 Dashboard 通过 `/ws/live` 做实时价格增强
**原因**:
- 页面职责清晰，便于后续独立迭代和问题定位
- API调用集中管理，减少重复请求逻辑与类型漂移
- WebSocket用于增强实时感，轮询继续承担兜底刷新，稳定性更高
**关键约束**:
- Market Mind页面必须支持手动编辑与历史追踪
- 决策历史必须可展开查看 `mind_alignment` 与 `bias_check`

## D011: Dashboard 首屏采用“图表优先 + API直连”实现
**日期**: 2026-02-12
**决策**: Phase 1主看板先实现轻量图表与信息卡片，采用 `lightweight-charts + Zustand` 直连后端 API，实时刷新先用轮询（15秒）稳定交付
**原因**:
- 尽快交付可观察界面，验证后端数据结构是否满足前端消费
- 轮询实现复杂度低，可先保障可用性，再在T019切换/补充 WebSocket 实时推送
- 页面结构已预留后续扩展到 `/mind`、`/decisions`、`/performance`
**关键约束**:
- 图表必须支持 `1h/4h/1d` 切换和买卖标注
- 信息面板必须暴露最新决策中的 `mind_alignment` 与 `bias_check`

## D010: Phase 1决策链路采用“可降级闭环”实现
**日期**: 2026-02-12
**决策**: 先实现完整分析闭环（行情拉取→AI决策→风控→纸盘执行→写入DB→API可读），其中AI推理采用确定性策略+Market Mind注入，后续再替换为真实LLM调用
**原因**:
- 在未配置外部密钥时系统仍可持续运行并验证全链路
- 确保决策输出始终满足结构化字段约束（尤其 `mind_alignment` 与 `bias_check`）
- 便于前端和Agent并行开发，不被模型接入阻塞
**关键约束**:
- 风控规则必须在执行前硬性校验，不能被AI输出绕过
- Market Mind修改必须继续写入 `market_mind_history`

## D009: 后端先做“契约优先”骨架（Mock API + SQLite + Market Mind服务）
**日期**: 2026-02-12
**决策**: Phase 1先实现完整后端API契约与数据骨架，再逐步替换mock逻辑为真实交易/行情逻辑
**原因**:
- 前端和Telegram Agent都依赖统一API，先稳定接口可并行开发
- 先落地Market Mind的load/save/update/history闭环，保证后续AI决策模块可直接接入
- SQLite 5张核心表先建好，避免后续模块开发时反复改基础设施
**关键约束**:
- 当前决策和行情接口可返回mock数据，但接口结构必须对齐 `docs/ARCHITECTURE.md`
- Market Mind每次修改必须写入 `market_mind_history`，确保可追溯

## D008: Market Mind — AI认知状态文档
**日期**: 2025-02-13
**决策**: 引入Market Mind作为AI的持续认知层——一份结构化JSON文档，包含市场信念、策略偏好、经验教训、偏误警觉、用户输入
**原因**:
- LLM每次调用无状态，没有Market Mind等于每次让陌生人做判断
- Market Mind让AI带着累积的认知做决策——它知道自己之前错在哪、什么信号最近有效
- 认知纠偏功能在此落地：用户已知偏误（如ETH过度乐观）在初始化时写入，AI每次决策前检查
- Phase 1手动维护，Phase 4自动更新，渐进式复杂度
**关键约束**: Market Mind不是数据库，而是"认知"——它记录的是判断和信念，不是原始数据

## D007: Overseer Agent — Telegram Bot
**日期**: 2025-02-13
**决策**: 构建7×24在线的Telegram Bot Agent，感知系统全部状态，主动通知并响应查询
**原因**: 用户不需要时刻盯Dashboard；Telegram是加密社区主流；Agent可以双向传递信息（包括用户观点写入Market Mind）
**关键约束**: Agent不做交易决策，决策由AI推理引擎负责

## D006: 前端技术选型 — Next.js + TypeScript
**日期**: 2025-02-12
**决策**: Next.js 14+ + Tailwind CSS + shadcn/ui + TradingView Lightweight Charts，前后端分离
**原因**: AI代码生成质量最高；TradingView是金融级K线图标准；前后端分离便于独立开发

## D005: AI调用方式 — 单次结构化调用
**日期**: 2025-02-12
**决策**: AI每次介入都是单次API调用，输入输出严格结构化（但注入Market Mind作为认知上下文）
**原因**: 可追溯、可靠、成本可控、可维护

## D004: 系统架构 — 确定性骨架 + AI大脑
**日期**: 2025-02-12
**决策**: 数据管道、风控、执行用确定性代码；AI只在市场解读、交易决策、复盘三个环节介入
**原因**: 涉及资金的流程必须可预测可审计

## D003: OpenClaw角色 — 迁移到新系统
**日期**: 2025-02-12
**决策**: OpenClaw功能迁移到新系统，Overseer Agent替代其通讯角色
**原因**: 减少复杂度，自我修改代码不稳定

## D002: 开发工具策略 — 多工具协作，文档为中心
**日期**: 2025-02-12
**决策**: Claude Code + OpenAI Codex + Claude.ai 协作，知识集中在 docs/
**原因**: 单一工具用量不够，文档保证上下文一致

## D001: 日线策略优先
**日期**: 2025-02-12
**决策**: 量化策略以日线(1d)为主
**原因**: 回测验证日线显著优于1h和4h
