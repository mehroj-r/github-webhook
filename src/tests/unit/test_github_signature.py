import hashlib
import hmac
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.utils.github import verify_signature

SECRET = "s3cr3t"
BODY = b'{"zen": "Keep it logically awesome."}'


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestVerifySignature:
    @pytest.mark.unit
    def test_valid_signature(self):
        assert verify_signature(BODY, _sign(BODY), secret=SECRET) is True

    @pytest.mark.unit
    def test_wrong_secret(self):
        assert verify_signature(BODY, _sign(BODY, "other"), secret=SECRET) is False

    @pytest.mark.unit
    def test_tampered_body(self):
        assert verify_signature(BODY + b" ", _sign(BODY), secret=SECRET) is False

    @pytest.mark.unit
    def test_missing_signature(self):
        assert verify_signature(BODY, None, secret=SECRET) is False

    @pytest.mark.unit
    def test_wrong_prefix(self):
        digest = hmac.new(SECRET.encode(), BODY, hashlib.sha256).hexdigest()
        assert verify_signature(BODY, "sha1=" + digest, secret=SECRET) is False

    @pytest.mark.unit
    def test_skipped_when_secret_not_configured(self):
        with patch("core.utils.github.settings") as mock_settings:
            mock_settings.GH_WEBHOOK_SECRET = ""
            assert verify_signature(BODY, None) is True
