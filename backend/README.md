# Backend Quick Start

## 1) Setup

```bash
cd backend
./scripts/setup_venv.sh
```

## 2) Run API

```bash
cd ..
PYTHONPATH=$(pwd) backend/.venv/bin/uvicorn backend.src.api.main:app --reload --port 8000
```

## 3) Trigger one analysis cycle

```bash
curl -X POST http://localhost:8000/api/system/trigger-analysis
```

## 4) Run Telegram Overseer Agent

```bash
cd ..
PYTHONPATH=$(pwd) backend/.venv/bin/python -m backend.src.agent.main
```
