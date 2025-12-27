from .base import BaseCommandValidator


class ConnectRepoCommandValidator(BaseCommandValidator):
    """Validator to check if the bot is connected to a chat."""

    arguments = ["repo_url"]
    error_msg = "Usage: /connect_repo https://github.com/username/repository"

    async def validate_repo_url(self, url: str) -> tuple[bool, str]:
        import re

        # Check if URL is provided
        if not url:
            return False, self.error_msg

        # Validate GitHub repository URL format
        pattern = r"^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$"
        if not bool(re.match(pattern, url)):
            return False, "Invalid GitHub repository URL."

        return True, ""
