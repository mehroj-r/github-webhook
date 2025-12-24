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

### Polling Mode (Development)
```bash
python -m src.main
```

Set `USE_WEBHOOK=false` in your `.env` file. The bot will use Telegram's long polling.

### Webhook Mode (Production)
Set `USE_WEBHOOK=true` in your `.env` file and run using one of the methods above. The bot will:
1. Start a FastAPI server on the specified HOST and PORT
2. Set up a webhook endpoint at `{WEBHOOK_URL}{WEBHOOK_PATH}`
3. Listen for incoming webhook requests from Telegram

The FastAPI server includes:
- `/` - Root endpoint (health check)
- `/health` - Health check endpoint
- `/webhook` (or your custom WEBHOOK_PATH) - Telegram webhook endpoint

## Architecture

The application integrates aiogram (Telegram bot framework) with FastAPI:

- **Polling Mode**: Only the aiogram bot runs, polling Telegram for updates
- **Webhook Mode**: FastAPI server runs with uvicorn, handling incoming webhook requests and feeding them to the aiogram dispatcher

Both the bot and server run in the same asyncio event loop, allowing seamless integration.

## Development

- Logs are stored in the `logs/` directory
- Set `DEBUG=true` for verbose logging
- Code formatting with Black


