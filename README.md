# GitHub Webhook to Telegram Bot

A Telegram bot integrated with FastAPI to receive GitHub webhooks and send notifications.

## Features

- **Dual Mode Support**: Run in either polling mode (for development) or webhook mode (for production)
- **FastAPI Integration**: Built-in FastAPI server for handling webhooks
- **Aiogram Framework**: Modern async Telegram bot framework
- **Graceful Shutdown**: Proper signal handling for clean shutdowns
- **Logging**: Comprehensive logging with separate files for errors and general logs

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Copy `.env.example` to `.env` and configure your settings:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your configuration:
   - `BOT_TOKEN`: Your Telegram bot token from @BotFather
   - `USE_WEBHOOK`: Set to `true` for webhook mode, `false` for polling
   - `WEBHOOK_URL`: Your public domain (e.g., `https://yourdomain.com`)
   - `WEBHOOK_SECRET`: Secret token for webhook validation
   - `HOST`: Server host (default: `0.0.0.0`)
   - `PORT`: Server port (default: `8000`)

## Connecting Repositories

### Option A: per-repository webhook

In the repository settings add a webhook with payload URL `https://<your-domain>/github/webhook`, content type
`application/json` and the secret from `GH_WEBHOOK_SECRET`. The initial `ping` registers the repository; then run
`/connect_repo https://github.com/owner/repo` in the Telegram chat.

### Option B: GitHub App (many repositories at once)

1. Create a GitHub App (Settings → Developer settings → GitHub Apps → New GitHub App):
   - **Webhook URL**: `https://<your-domain>/github/webhook`
   - **Webhook secret**: the value of `GH_WEBHOOK_SECRET`
   - **Repository permissions** (read-only): Metadata, plus whatever you want notifications for, e.g. Contents
     (push), Pull requests, Issues, Actions (workflow runs), Checks, Deployments, Dependabot alerts,
     Secret scanning alerts
   - **Subscribe to events** matching those permissions
2. Install the app on an account and pick repositories. The `installation` event registers every selected
   repository (unconnected); `/connect_repo` links each one to a chat as usual.
3. Adding repositories to the installation registers them; removing them, suspending or uninstalling the app
   stops their notifications and tells the connected chat. Re-adding or unsuspending resumes them.

No private key or API access is needed: everything is driven by webhook payloads.

## Inline GitHub Actions (optional)

Set `GH_TOKEN` to a token that can write Actions and Pull requests on your repositories (a fine-grained PAT, or a
bot account's token). Notifications then get buttons, usable by chat administrators only:

- failed or timed-out workflow runs: **Re-run failed jobs**
- opened / reopened / ready-for-review pull requests: **Approve** and **Merge** (asks for confirmation; method from
  `GH_MERGE_METHOD`: `merge`, `squash` or `rebase`)

Actions are performed as the token's owner. `GH_API_URL` can point at a GitHub Enterprise Server API.

## Running the Bot

### Development (Polling Mode)
```bash
python -m src.main
```

Set `USE_WEBHOOK=false` in your `.env` file. The bot will use Telegram's long polling with a single process and auto-reload.

### Production (Webhook Mode with Docker) - Recommended
```bash
# Build and start with Gunicorn + Uvicorn workers
docker-compose up -d --build

# View logs
docker-compose logs -f app

# Scale workers
WORKERS=8 docker-compose up -d --build
```

Set `USE_WEBHOOK=true` in your `.env` file. The application will run with:
- **Gunicorn** as the process manager
- **Multiple Uvicorn workers** for ASGI support and async capabilities
- Automatic database migrations on startup
- Health checks and auto-restart

### Production (Manual Deployment)
```bash
# Run migrations
uv run alembic -c src/database/alembic.ini upgrade head

# Start with Gunicorn + Uvicorn workers
gunicorn asgi:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --config gunicorn.conf.py
```

## Production Features

- ✅ **Multi-worker deployment** with Gunicorn + Uvicorn
- ✅ **Async/ASGI support** for high performance
- ✅ **Automatic worker restarts** to prevent memory leaks
- ✅ **Graceful shutdowns** with zero downtime
- ✅ **Horizontal scaling** by adjusting worker count
- ✅ **Production-ready** logging and monitoring

**Worker Configuration:**
- Set `WORKERS` environment variable (default: 4)
- Recommended: `(CPU cores × 2) + 1`
- Each worker handles requests concurrently via async/await

## Logging

Set `LOG_FORMAT=json` to emit one JSON object per line (console and log files). Records logged while a GitHub
delivery is being handled carry its `delivery_id`; `extra={...}` fields become top-level keys.

## FastAPI Endpoints

The FastAPI server includes:
- `/` - Root endpoint (health check)
- `/misc/health` - Health check: database (`SELECT 1`) and Telegram (`get_me`, cached 60s); 503 only when the database is down
- `/misc/metrics` - Prometheus metrics (`gh_webhook_deliveries_total`, `telegram_request_duration_seconds`); set `PROMETHEUS_MULTIPROC_DIR` when running several Gunicorn workers (the Docker image does); protect it with `METRICS_TOKEN`
- `/webhook` (or your custom WEBHOOK_PATH) - Telegram webhook endpoint
- `/admin` - Admin dashboard (chats, repositories, deliveries, digest items, bot admins). Enabled by setting
  `ADMIN_PASSWORD` (user `ADMIN_USERNAME`, default `admin`); protected by HTTP Basic auth, so serve it over HTTPS only

## Architecture

The application supports two deployment modes:

### Development Mode (Polling)
- Single process with aiogram bot
- Long polling for Telegram updates
- Auto-reload on code changes
- Best for: Local development and testing

### Production Mode (Webhook)
- **Gunicorn** master process managing multiple workers
- **Uvicorn workers** with ASGI support for async/await
- FastAPI server handling GitHub and Telegram webhooks
- Horizontal scaling via worker count
- Best for: Production deployment with high traffic

```
Gunicorn Master
├── Uvicorn Worker 1 (FastAPI + Bot)
├── Uvicorn Worker 2 (FastAPI + Bot)
├── Uvicorn Worker 3 (FastAPI + Bot)
└── Uvicorn Worker 4 (FastAPI + Bot)
```

Each worker runs independently, handling requests concurrently with async capabilities.

## Development

- Logs are stored in the `logs/` directory
- Set `DEBUG=true` for verbose logging
- Code formatting with Black

## Task Runner (just)

This project uses a root `justfile` instead of a custom Python management CLI.

```bash
# List available tasks
just

# Run app
just run

# Database migrations
just makemigrations message="add_new_field"
just migrate
just downgrade revision=-1

# Database utilities
just createdb
just dropdb yes=true
just resetdb yes=true
just showtables

# Quality checks
just lint
just format
just ty
just test
just check
```

