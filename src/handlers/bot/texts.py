"""User-facing help texts for bot commands."""

HELP_TEXT = (
    "<b>🤖 GitHub Webhook Bot</b>\n\n"
    "Connect GitHub repositories to this chat and receive notifications about pushes, "
    "pull requests, issues, releases, workflows and more.\n\n"
    "<b>Setup</b>\n"
    "1. In your GitHub repository open <i>Settings → Webhooks</i> and add the bot's webhook URL "
    "with content type <code>application/json</code> and the shared secret.\n"
    "2. GitHub sends a <code>ping</code> event which registers the repository.\n"
    "3. Run <code>/connect_repo https://github.com/owner/repo</code> here.\n\n"
    "<b>Commands</b>\n"
    "/connect_repo &lt;url&gt; — connect a registered repository to this chat\n"
    "/disconnect_repo &lt;url&gt; — stop notifications for a repository in this chat\n"
    "/repos — list repositories connected to this chat\n"
    "/deliveries — show the latest webhook deliveries for connected repositories\n"
    "/help — show this message"
)
