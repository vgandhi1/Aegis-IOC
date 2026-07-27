"""Signing-key policy tests.

A forgeable AEGIS_SECRET_KEY is a full auth bypass, so every rejection path is
covered here rather than left to review.
"""

import pytest
from pydantic import ValidationError

from app.config import MIN_SECRET_KEY_LENGTH, Settings

GOOD_KEY = "x" * MIN_SECRET_KEY_LENGTH


def test_local_without_key_generates_ephemeral_key():
    settings = Settings(environment="local", secret_key="")
    assert len(settings.secret_key) >= MIN_SECRET_KEY_LENGTH


def test_generated_keys_differ_between_instances():
    first = Settings(environment="local", secret_key="")
    second = Settings(environment="local", secret_key="")
    assert first.secret_key != second.secret_key


@pytest.mark.parametrize("environment", ["production", "staging", "prod", "demo"])
def test_non_local_without_key_refuses_to_start(environment):
    with pytest.raises(ValidationError, match="AEGIS_SECRET_KEY is required"):
        Settings(environment=environment, secret_key="")


def test_published_key_is_refused_even_locally():
    with pytest.raises(ValidationError, match="published"):
        Settings(environment="local", secret_key="local-dev-only-change-me-please-32+chars")


def test_short_key_is_refused():
    with pytest.raises(ValidationError, match="at least"):
        Settings(environment="production", secret_key="too-short")


def test_explicit_key_is_kept_and_stripped():
    settings = Settings(environment="production", secret_key=f"  {GOOD_KEY}  ")
    assert settings.secret_key == GOOD_KEY


def test_whitespace_only_key_is_treated_as_missing():
    with pytest.raises(ValidationError, match="AEGIS_SECRET_KEY is required"):
        Settings(environment="production", secret_key="   ")
