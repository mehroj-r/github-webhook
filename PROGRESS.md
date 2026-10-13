# Progress Log

Working notes for continuing the feature roadmap. Each feature lands as one commit on `production`,
with `ruff check`, `ruff format`, `ty`, `pytest` and `alembic heads` passing before the commit.

## Check command (run before every commit)

```bash
uv run ruff check . --fix && uv run ruff format .
uv run ty check src --extra-search-path src --exclude migrations --exclude src/tests --exclude tests --exclude test
uv run pytest -q
uv run alembic -c src/database/alembic.ini heads
```

## Conventions established so far

- **One feature = one commit**, message `feat(<area>): ...` with a short bullet list of what changed.
- **Schema changes** get a hand-written Alembic migration under `src/database/migrations/versions/`
  (copy the style of the existing ones; `migrations` is excluded from ruff/ty).
- **Notifications** always go through `core/notifications.py`:
  `resolve_target()` (chat lookup, paused/muted/inactive, event filter, branch filter) then
  `notify()` / `notify_or_edit()` (template rendering, digest queueing, forum topic, retries).
  New GitHub handlers must not call `bot.send_message` directly.
- **Bot commands** that change settings use `ChatAdminFilter()` and `_pick_repo()` in
  `src/handlers/bot/settings.py`; add every new command to `src/handlers/bot/texts.py` (HELP_TEXT).
- **Dedicated GitHub handlers** live in `src/handlers/github/events/<event>.py` with
  `build_message(event)` / `build_buttons(event)` so they are unit-testable; the generic fallback in
  `generic.py` registers only for events without a dedicated handler.
- **Tests**: unit tests mock everything; integration tests use the `sqlite_session_maker` fixture
  from `src/tests/conftest.py` (in-memory SQLite with all tables). Realistic GitHub payloads are in
  `src/tests/payloads.py`. Patch `core.bot.bot` with a `MagicMock` to capture Telegram calls.
- `__pycache__` is gitignored; `.dockerignore` keeps `.env`, tests and logs out of the image.

## Done (newest first)

| Commit | Feature | Notes |
| --- | --- | --- |
| `_pending_` | Inline GitHub actions | `core/github_api.py` (aiohttp; `GH_TOKEN`, `GH_API_URL`, `GH_MERGE_METHOD`): re-run failed jobs, approve, merge. Buttons from `handlers/github/actions.py` (callback `gh:<action>:<repo uuid hex>:<number>`, carried in `url_buttons` as `callback:<data>` entries, rendered as one bottom row); callbacks in `handlers/bot/actions.py` behind `ChatAdminFilter` + repo-belongs-to-chat check; merge asks for confirmation in a reply. Compact template keeps action buttons; digest uses `first_url()` |
| `876559b` | Admin web dashboard | `api/admin.py`: sqladmin at `/admin`, mounted from `setup_api_routers()` only when `ADMIN_PASSWORD` is set (`ADMIN_USERNAME`, default `admin`). `BasicAuthMiddleware` (constant-time compare) also rejects cross-site writes by Origin/Referer vs Host/X-Forwarded-Host since sqladmin has no CSRF tokens. Views: chats, repositories (editable, no create), deliveries and digest items (read-only), bot admins |
| `1164608` | `bot_admins` table | `BotAdmin` model (migration `5b7d9f2a4c63`); `/admins`, `/admin_add <user_id> [name]` (or reply), `/admin_remove` in `handlers/bot/admins.py` behind `BotOwnerFilter` (MASTER_CHAT_ID only). `is_bot_admin()` opens its own session; bot admins pass `ChatAdminFilter` in any group; DB errors fall back to the Telegram admin check |
| `d41d124` | GitHub App installation flow | `handlers/github/events/installation.py`: `installation` created/new_permissions_accepted register repos (unconnected, url built from `full_name`), suspend/deleted deactivate by stored `gh_repos.installation_id` (migration `4a6c8e1f3b52`) or payload names, unsuspend reactivates; `installation_repositories` added/removed. Connected chats get a "Notifications stopped" notice via `notify()` without session (bypasses digest). README "Connecting Repositories" |
| `8d2a316` | Structured JSON logging | `LOG_FORMAT=text|json`; `JsonFormatter` (one object per line, `extra=` fields as keys) and `ContextFilter` on every handler in `core/utils/logger.py`; `delivery_id_var` contextvar set in the GitHub route and around `_run_handler()` |
| `e075701` | Metrics + health | `core/metrics.py`: `gh_webhook_deliveries_total{event,status}` (recorded in `_finish_delivery`, plus `duplicate`), `telegram_request_duration_seconds{method,outcome}` (around `with_retry`; method = first word of `description`). `/misc/metrics` (optional `METRICS_TOKEN` bearer). Multi-worker via `PROMETHEUS_MULTIPROC_DIR` (set in Dockerfile, wiped in `entrypoint.sh`, `child_exit` hook). `/misc/health` checks DB `SELECT 1` + cached `get_me` (60s); 503 only if DB is down, Telegram outage = `degraded` |
| `7044a71` | Background webhook processing | `WEBHOOK_PROCESS_IN_BACKGROUND` (default true): after validation the route returns `{"status": "accepted"}` and runs `_run_handler()` via FastAPI `BackgroundTasks`; outcome only in the delivery log. Validation errors stay synchronous (400/401). Sync mode keeps `processed`/500 |
| `786fe83` | CI workflow | `.github/workflows/ci.yml` (ruff, ty, pytest, single Alembic head) on push/PR and as `workflow_call`; `deploy.yml` runs it as job `ci` and `build-and-deploy` `needs: ci`. Tests need placeholder `BOT_TOKEN`/`DATABASE_URL` (sqlite+aiosqlite) |
| `45c54f3` | Digest mode | `/digest [repo] 1h|off|now`, `tg_digest_items`, scheduler in `core/digest.py` started from `asgi.py` and `main.py`, flush under `distributed_lock("digest_flush")` |
| `29d350b` | Message templates | `/template compact|verbose`, `tg_chats.template`, `compact_text()` in `core/notifications.py` |
| `049134b` | Telegram retries | `with_retry()` in `core/utils/bot.py`: RetryAfter (<=60s) and network errors, 4 attempts |
| `de23c40` | Workflow run message editing | `tg_sent_messages`, `notify_or_edit()`; key `workflow_run:<id>:<attempt>` |
| `fa3ef0e` | Dedicated event handlers | pull_request, pull_request_review, issues, issue_comment, release, workflow_run, check_suite, deployment_status, dependabot_alert, secret_scanning_alert; helpers in `handlers/github/formatting.py` |
| `13a4daf` | `/status` (`/settings`) | per-repo settings + last delivery |
| `131731b` | Forum topic routing | `/topic [repo]` inside a topic, `gh_repos.message_thread_id` |
| `9e492ff` | `/pause` `/resume` | reuses `gh_repos.is_active` |
| `4024f51` | Branch filters + mute | `/filter_branches`, `/mute`, `/unmute`; `core/utils/duration.py` |
| `6ba38ed` | Event filters | `/events` inline keyboard, `handlers/github/catalog.py`, `gh_repos.enabled_events`; central `resolve_target()` |
| `2285a36` | Admin-only management | `handlers/bot/filters/admin.py`, `tg_chats.managed_by_user_id` |
| `657744b` | `/disconnect_repo` `/repos` `/help` | |
| `5960c6a` | Delivery log | `gh_deliveries`, idempotent redeliveries, `/deliveries` |
| `78e23d0` | Review fixes | signature verification, payload models, lifecycle, ops |

Migrations head after this work: `5b7d9f2a4c63`. Run `just migrate` on every environment.

## Behavior changes already shipped (tell users)

- Events outside the curated catalog are off by default; enable via the "Other events" toggle in `/events`.
- Noisy PR/issue actions (synchronize, labeled, edited, ...) are skipped.
- Telegram handler errors return 200 (logged) so one bad update cannot block the queue.
- GitHub deliveries are acknowledged with `{"status": "accepted"}` before handling; handler failures no longer
  return 500 (see `/deliveries`). Set `WEBHOOK_PROCESS_IN_BACKGROUND=false` for the old behavior.
- In groups only admins (or the bot owner `MASTER_CHAT_ID`, or a bot admin from `/admin_add`) can run management commands.

## Remaining roadmap (suggested order)

1. **Pairing code on connect** (ownership check): ping handler generates a code, surfaced in the
   webhook delivery response body / master chat; `/connect_repo <url> <code>` required.

## Not addressed / known limitations

- `Bot(...)` and the DB engine are created at import time; the app cannot be imported without a
  valid `BOT_TOKEN` and `DATABASE_URL`.
- Repo-to-chat is 1:1 (`gh_repos.chat_id`); all per-repo settings live on `gh_repos`. Fan-out to
  multiple chats would need a join table and moving settings there.
- Digest scheduler uses a Postgres advisory lock; on SQLite (tests) `flush_due_digests()` is called
  directly.
- `/status` and `/deliveries` are open to all chat members; only settings commands are admin-gated.
