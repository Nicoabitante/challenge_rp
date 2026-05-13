from pathlib import Path

import pytest

from config.database import database_config_from_url


def test_database_config_defaults_to_sqlite():
    config = database_config_from_url(None, base_dir=Path("/app"))

    assert config == {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path("/app/db.sqlite3"),
    }


def test_database_config_parses_postgres_url():
    config = database_config_from_url(
        "postgres://user:pass@db:5432/challenge_rp?sslmode=disable",
        base_dir=Path("/app"),
    )

    assert config == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "challenge_rp",
        "USER": "user",
        "PASSWORD": "pass",
        "HOST": "db",
        "PORT": "5432",
        "OPTIONS": {"sslmode": "disable"},
    }


def test_database_config_rejects_unsupported_scheme():
    with pytest.raises(ValueError):
        database_config_from_url("mysql://user:pass@db/app", base_dir=Path("/app"))
