# Deployment Guide (VPS)

## Assumptions

- Project path: `/opt/trading-system`
- Runtime user: `ubuntu`
- Backend binds `127.0.0.1:8000`
- Frontend binds `127.0.0.1:3000`

## 1) Prepare backend and frontend

```bash
cd /opt/trading-system/backend
./scripts/setup_venv.sh

cd /opt/trading-system/frontend
npm install
npm run build
```

## 2) Configure environment

```bash
cp /opt/trading-system/backend/.env.example /opt/trading-system/backend/.env
# fill TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / API keys
```

## 3) Install services and nginx

```bash
cd /opt/trading-system
./deploy/scripts/preflight.sh
PUBLIC_DOMAIN=trade.example.com DEPLOY_USER=ubuntu PROJECT_DIR=/opt/trading-system ./deploy/scripts/install_services.sh
```

## 4) Verify

```bash
./deploy/scripts/post_deploy_check.sh
```

## Notes

- `deploy/systemd/*.service` may need `User` and `WorkingDirectory` adjustments.
- `deploy/nginx/trading-system.conf` must replace `trade.your-domain.com`.
- Add TLS with certbot after nginx site is enabled.
- 可配置参数（install/render脚本读取）：`PROJECT_DIR` (默认 `/opt/trading-system`)
- 可配置参数（install/render脚本读取）：`DEPLOY_USER` (默认 `ubuntu`)
- 可配置参数（install/render脚本读取）：`PUBLIC_DOMAIN` (默认 `trade.your-domain.com`)
- 可配置参数（install/render脚本读取）：`BACKEND_HOST` (默认 `127.0.0.1`)
- 可配置参数（install/render脚本读取）：`BACKEND_PORT` (默认 `8000`)
- 可配置参数（install/render脚本读取）：`FRONTEND_PORT` (默认 `3000`)
- 可配置参数（install/render脚本读取）：`FRONTEND_API_BASE_URL` (默认 `https://$PUBLIC_DOMAIN`)
