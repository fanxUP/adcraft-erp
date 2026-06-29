"""Tests for security utilities: password hashing and JWT token management."""

import time
from unittest.mock import patch

import pytest

from app.utils.security import hash_password, verify_password, create_access_token, decode_access_token
from tests.conftest import SAMPLE_USER_ID, TEST_USERNAME, TEST_PASSWORD


class TestPasswordHashing:
    def test_hash_and_verify_success(self):
        """Hashing a password then verifying with the same password returns True."""
        hashed = hash_password(TEST_PASSWORD)
        assert hashed != TEST_PASSWORD
        assert verify_password(TEST_PASSWORD, hashed) is True

    def test_hash_is_unique_per_call(self):
        """Each call to hash_password produces a different hash (different salt)."""
        h1 = hash_password(TEST_PASSWORD)
        h2 = hash_password(TEST_PASSWORD)
        assert h1 != h2

    def test_verify_wrong_password(self):
        """Verifying with the wrong password returns False."""
        hashed = hash_password(TEST_PASSWORD)
        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_empty_password(self):
        """Empty string password is handled without error."""
        hashed = hash_password(TEST_PASSWORD)
        assert verify_password("", hashed) is False


class TestJWTToken:
    def test_create_and_decode(self):
        """A created token can be decoded and contains correct claims."""
        token = create_access_token(SAMPLE_USER_ID, TEST_USERNAME)
        payload = decode_access_token(token)
        assert payload["sub"] == str(SAMPLE_USER_ID)
        assert payload["username"] == TEST_USERNAME
        assert "iat" in payload
        assert "exp" in payload

    def test_decode_invalid_token(self):
        """An invalid token raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token("this.is.not.a.valid.jwt")

    def test_decode_tampered_token(self):
        """A token with a modified signature raises ValueError."""
        token = create_access_token(SAMPLE_USER_ID, TEST_USERNAME)
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalidsignature"
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token(tampered)

    def test_decode_malformed_token(self):
        """A malformed token raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token("not-a-token")

    @patch("app.utils.security.settings.JWT_EXPIRE_MINUTES", -1)
    def test_expired_token_raises(self):
        """A token with a past expiration raises ValueError."""
        token = create_access_token(SAMPLE_USER_ID, TEST_USERNAME)
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token(token)
