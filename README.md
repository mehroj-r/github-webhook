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
python -m manage migrate

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

## FastAPI Endpoints

The FastAPI server includes:
- `/` - Root endpoint (health check)
- `/health` - Health check endpoint
- `/webhook` (or your custom WEBHOOK_PATH) - Telegram webhook endpoint

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


