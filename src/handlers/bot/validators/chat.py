import re

from core.utils.command_validator import BaseCommandValidator

GITHUB_REPO_URL_PATTERN = re.compile(r"^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$")


class RepoUrlCommandValidator(BaseCommandValidator):
    """Validate a single GitHub repository URL argument."""

    arguments = ["repo_url"]
    command = "connect_repo"

    @property
    def error_msg(self) -> str:  # type: ignore[override]
        return f"Usage: /{self.command} https://github.com/username/repository"

    async def validate_repo_url(self, url: str) -> tuple[bool, str]:
        # Check if URL is provided
        if not url:
            return False, self.error_msg

        # Validate GitHub repository URL format
        if not GITHUB_REPO_URL_PATTERN.match(url):
            return False, "Invalid GitHub repository URL."

        return True, ""


class ConnectRepoCommandValidator(RepoUrlCommandValidator):
    command = "connect_repo"


class DisconnectRepoCommandValidator(RepoUrlCommandValidator):
    command = "disconnect_repo"
