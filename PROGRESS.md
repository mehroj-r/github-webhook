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
| `_pending_` | Structured JSON logging | `LOG_FORMAT=text|json`; `JsonFormatter` (one object per line, `extra=` fields as keys) and `ContextFilter` on every handler in `core/utils/logger.py`; `delivery_id_var` contextvar set in the GitHub route and around `_run_handler()` |
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

Migrations head after this work: `2d7e5f8a9b41`. Run `just migrate` on every environment.

## Behavior changes already shipped (tell users)

- Events outside the curated catalog are off by default; enable via the "Other events" toggle in `/events`.
- Noisy PR/issue actions (synchronize, labeled, edited, ...) are skipped.
- Telegram handler errors return 200 (logged) so one bad update cannot block the queue.
- GitHub deliveries are acknowledged with `{"status": "accepted"}` before handling; handler failures no longer
  return 500 (see `/deliveries`). Set `WEBHOOK_PROCESS_IN_BACKGROUND=false` for the old behavior.
- In groups only admins (or the bot owner `MASTER_CHAT_ID`) can run management commands.

## Remaining roadmap (suggested order)

1. **GitHub App installation flow**: handle `installation` (created, with `repositories`) and
   `installation_repositories` (added/removed) to register/deactivate `GithubRepository` rows; no API
   calls required. Document app setup in README.
2. **`bot_admins` table**: runtime-managed admins instead of the single `MASTER_CHAT_ID`;
   `/admins`, `/admin_add <user_id>`, `/admin_remove <user_id>` (owner only). The admin filter should
   open its own session via `async_session_maker` (inner middleware data is not available to filters).
3. **Admin web dashboard**: `sqladmin` mounted at `/admin` with basic auth from settings
   (`ADMIN_USERNAME` / `ADMIN_PASSWORD`); views for chats, repos, deliveries, digest items.
4. **Inline GitHub actions**: needs `GH_TOKEN` setting and an aiohttp client; buttons to re-run a
   failed workflow and merge/approve a PR via callback queries (`gh:rerun:<repo>:<run_id>`), admin-only,
   with tests mocking HTTP.
5. **Pairing code on connect** (ownership check): ping handler generates a code, surfaced in the
   webhook delivery response body / master chat; `/connect_repo <url> <code>` required.

## Not addressed / known limitations

- `Bot(...)` and the DB engine are created at import time; the app cannot be imported without a
  valid `BOT_TOKEN` and `DATABASE_URL`.
- Repo-to-chat is 1:1 (`gh_repos.chat_id`); all per-repo settings live on `gh_repos`. Fan-out to
  multiple chats would need a join table and moving settings there.
- Digest scheduler uses a Postgres advisory lock; on SQLite (tests) `flush_due_digests()` is called
  directly.
- `/status` and `/deliveries` are open to all chat members; only settings commands are admin-gated.
