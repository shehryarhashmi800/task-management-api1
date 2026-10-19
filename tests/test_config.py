import pytest
from pydantic import ValidationError

from app.config import Settings

STRONG_KEY = "k" * 48


def make(**overrides):
    return Settings(_env_file=None, **overrides)


def test_development_allows_the_default_secret():
    assert make().SECRET_KEY


@pytest.mark.parametrize(
    "bad_key",
    ["short", "insecure-dev-secret-change-me", "change-this-to-a-long-random-string-in-production"],
)
def test_production_refuses_weak_secrets(bad_key):
    with pytest.raises(ValidationError):
        make(ENVIRONMENT="production", SECRET_KEY=bad_key)


def test_production_accepts_a_strong_secret():
    assert make(ENVIRONMENT="production", SECRET_KEY=STRONG_KEY).is_production


def test_environment_name_is_case_insensitive():
    with pytest.raises(ValidationError):
        make(ENVIRONMENT=" Production ", SECRET_KEY="short")


def test_cors_origins_are_split_and_trimmed():
    settings = make(CORS_ORIGINS=" https://a.example , https://b.example ,, ")
    assert settings.cors_origins_list == ["https://a.example", "https://b.example"]


def test_empty_sentry_dsn_is_treated_as_unset():
    assert make(SENTRY_DSN="   ").SENTRY_DSN is None


def test_proxy_headers_are_trusted_by_default_only_in_production():
    assert make().trust_proxy_headers is False
    assert make(ENVIRONMENT="production", SECRET_KEY=STRONG_KEY).trust_proxy_headers is True
    assert make(TRUST_PROXY_HEADERS=True).trust_proxy_headers is True
    explicit_off = make(ENVIRONMENT="production", SECRET_KEY=STRONG_KEY, TRUST_PROXY_HEADERS=False)
    assert explicit_off.trust_proxy_headers is False
