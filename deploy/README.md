# Dev server deployment (gh.mekhroj.uz)

The dev instance runs on `ideal-dev-server` from a checkout of the `production` branch at
`/root/github-webhook`, built on the server with Docker Compose. Every push to `production` deploys it
through the `deploy-dev` job in `.github/workflows/deploy.yml`, next to (and independent of) the prod deploy.

## Layout on the server

| What | Where |
| --- | --- |
| Checkout + `.env` | `/root/github-webhook` |
| Containers | `gh-webhook-app-dev` (127.0.0.1:8120), `gh-webhook-db-dev` (127.0.0.1:5460) |
| nginx site | `/etc/nginx/sites-available/gh.mekhroj.uz` (copy of `deploy/nginx/gh.mekhroj.uz`) |
| TLS | Cloudflare origin certificate `/etc/nginx/ssl/mekhroj-origin.*`, DNS proxied through Cloudflare |

## Secrets

Repository secrets used by `deploy-dev`: `DEV_SSH_HOST`, `DEV_SSH_USER`, `DEV_SSH_PRIVATE_KEY`. The matching
public key sits in the server's `/root/.ssh/authorized_keys` with the `restrict` option.

App credentials live only in the server's `.env` (never in the repo). The dev bot must use its **own**
`BOT_TOKEN`: Telegram allows one webhook per bot, so sharing the prod token would steal prod's webhook.

## Manual deploy

```bash
cd ~/github-webhook
git fetch origin production && git checkout production && git merge --ff-only origin/production
docker compose up -d --build --remove-orphans
```

Migrations run in the container entrypoint. Logs: `docker compose logs -f app`.

## nginx changes

```bash
cp ~/github-webhook/deploy/nginx/gh.mekhroj.uz /etc/nginx/sites-available/gh.mekhroj.uz
nginx -t && systemctl reload nginx
```
