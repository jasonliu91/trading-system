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
./deploy/scripts/install_services.sh
```

## 4) Verify

```bash
sudo systemctl status trading-backend trading-agent trading-frontend
curl http://127.0.0.1:8000/api/system/health
```

## Notes

- `deploy/systemd/*.service` may need `User` and `WorkingDirectory` adjustments.
- `deploy/nginx/trading-system.conf` must replace `trade.your-domain.com`.
- Add TLS with certbot after nginx site is enabled.

