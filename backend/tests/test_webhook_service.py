"""Tests for webhook service (match-02).

Coverage: HMAC-SHA256 signature generation/verification, webhook push config.
"""
import pytest
import json
import time

from app.services.webhook_service import (
    _generate_signature,
    verify_webhook_signature,
    push_demand_to_agent,
    MAX_RETRIES,
    RETRY_DELAYS,
)


class TestWebhookSignatureGeneration:
    """Test _generate_signature."""

    def test_generates_hex_string(self):
        """Should produce a valid hex digest."""
        sig = _generate_signature("1234567890", "secret", '{"test":1}')
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex length
        int(sig, 16)  # Should be valid hex

    def test_deterministic(self):
        """Same input should produce same signature."""
        sig1 = _generate_signature("1234567890", "secret", '{"test":1}')
        sig2 = _generate_signature("1234567890", "secret", '{"test":1}')
        assert sig1 == sig2

    def test_different_secret_different_result(self):
        """Different secret should produce different signature."""
        sig1 = _generate_signature("1234567890", "secret1", '{"test":1}')
        sig2 = _generate_signature("1234567890", "secret2", '{"test":1}')
        assert sig1 != sig2

    def test_different_timestamp_different_result(self):
        """Different timestamp should produce different signature."""
        sig1 = _generate_signature("1234567890", "secret", '{"test":1}')
        sig2 = _generate_signature("9999999999", "secret", '{"test":1}')
        assert sig1 != sig2

    def test_empty_body(self):
        """Should handle empty body."""
        sig = _generate_signature("1234567890", "secret", "")
        assert len(sig) == 64


class TestWebhookSignatureVerification:
    """Test verify_webhook_signature."""

    def test_valid_signature(self):
        """Correct signature should verify as True."""
        timestamp = "1234567890"
        secret = "my_secret"
        body = '{"event":"demand.pushed"}'
        signature = _generate_signature(timestamp, secret, body)
        assert verify_webhook_signature(timestamp, signature, body, secret) is True

    def test_invalid_signature(self):
        """Wrong signature should verify as False."""
        timestamp = "1234567890"
        secret = "my_secret"
        body = '{"event":"demand.pushed"}'
        assert verify_webhook_signature(timestamp, "invalid_sig", body, secret) is False

    def test_wrong_secret(self):
        """Wrong secret should verify as False."""
        timestamp = "1234567890"
        body = '{"event":"demand.pushed"}'
        signature = _generate_signature(timestamp, "correct_secret", body)
        assert verify_webhook_signature(timestamp, signature, body, "wrong_secret") is False

    def test_tampered_body(self):
        """Tampered body should verify as False."""
        timestamp = "1234567890"
        secret = "my_secret"
        body = '{"event":"demand.pushed"}'
        signature = _generate_signature(timestamp, secret, body)
        tampered_body = '{"event":"demand.cancelled"}'
        assert verify_webhook_signature(timestamp, signature, tampered_body, secret) is False


class TestWebhookConfig:
    """Test webhook configuration constants."""

    def test_max_retries(self):
        """MAX_RETRIES should be 5."""
        assert MAX_RETRIES == 5

    def test_retry_delays(self):
        """RETRY_DELAYS should have 4 entries."""
        assert len(RETRY_DELAYS) == 4
        # Delays should be in ascending order
        for i in range(len(RETRY_DELAYS) - 1):
            assert RETRY_DELAYS[i] < RETRY_DELAYS[i + 1]


class TestWebhookPushBehavior:
    """Test push_demand_to_agent behavior (no real HTTP)."""

    @pytest.mark.asyncio
    async def test_push_invalid_url_returns_failure(self):
        """Pushing to invalid URL should return failure after retries."""
        result = await push_demand_to_agent(
            webhook_url="http://localhost:19999/nonexistent",
            webhook_secret="test",
            demand_data={"id": "test", "title": "Test demand"},
        )
        assert result["success"] is False
        assert "event_id" in result
        assert result["retries"] == MAX_RETRIES
