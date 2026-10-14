# Contributing

Thanks for your interest! Bug reports, ideas and pull requests are welcome.

## Getting Started

```bash
uv sync
cp .env.example .env   # fill in BOT_TOKEN etc.
uv run pre-commit install
python -m src.main     # polling mode for local development
```

## Before Opening a Pull Request

```bash
uv run ruff check . --fix
uv run ruff format .
uv run pytest
```

- Keep changes focused; one topic per pull request.
- Add or update tests in `src/tests/` when behaviour changes (markers: `unit`, `integration`, `async_`).
- Database model changes need an Alembic migration (`just makemigrations message="..."`).
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat(scope): ...`,
  `fix: ...`, `docs: ...`).
- Pull requests target the `production` branch and are squash-merged.

See [`AGENTS.md`](AGENTS.md) for the full code style guide and command reference.

## Questions and Security

Ask questions in [Discussions](https://github.com/mehroj-r/github-webhook/discussions). Report vulnerabilities
privately as described in [`SECURITY.md`](SECURITY.md).

By participating you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
