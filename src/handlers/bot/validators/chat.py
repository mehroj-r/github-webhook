import re

from core.utils.command_validator import BaseCommandValidator

GITHUB_REPO_URL_PATTERN = re.compile(r"^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$")
PAIRING_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{4,16}$")


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
    """Repository URL plus the pairing code from the repository's ping delivery (optional for bot admins)."""

    arguments = ["repo_url", "code"]
    command = "connect_repo"

    @property
    def error_msg(self) -> str:  # type: ignore[override]
        return f"Usage: /{self.command} https://github.com/username/repository PAIRINGCODE"

    async def validate_code(self, code: str) -> tuple[bool, str]:
        if code and not PAIRING_CODE_PATTERN.match(code):
            return False, "Invalid pairing code."
        return True, ""


class DisconnectRepoCommandValidator(RepoUrlCommandValidator):
    command = "disconnect_repo"
