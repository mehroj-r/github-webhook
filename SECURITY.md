# Security Policy

## Supported Versions

Only the latest release and the `production` branch receive security fixes.

## Reporting a Vulnerability

Please **do not** open a public issue for security problems.

Report privately through GitHub: **Security → Report a vulnerability**
(<https://github.com/mehroj-r/github-webhook/security/advisories/new>).

Include what you found, how to reproduce it, and the impact you expect. You should get a reply within a few days;
once a fix is released, the advisory is published with credit unless you prefer otherwise.

Particularly relevant areas: webhook signature verification (`GH_WEBHOOK_SECRET`), Telegram webhook secret
handling, pairing codes, the admin dashboard, and anything that acts with `GH_TOKEN` (re-run, approve, merge).
