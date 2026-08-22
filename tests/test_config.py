"""Tests for environment-backed settings."""

from pathlib import Path

import pytest

from config import Settings


def test_settings_load_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATA_GO_KR_SERVICE_KEY=dotenv-key\n"
        "HTTP_TIMEOUT_SECONDS=12\n"
        "WALKING_SPEED_M_PER_MINUTE=55\n",
        encoding="utf-8",
    )
    for name in (
        "DATA_GO_KR_SERVICE_KEY",
        "HTTP_TIMEOUT_SECONDS",
        "WALKING_SPEED_M_PER_MINUTE",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings.from_env(env_file)

    assert settings.data_go_kr_service_key == "dotenv-key"
    assert settings.http_timeout_seconds == 12
    assert settings.walking_speed_m_per_minute == 55
    assert settings.data_mode == "file"


def test_environment_takes_precedence_over_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATA_GO_KR_SERVICE_KEY=dotenv-key\n", encoding="utf-8")
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", "shell-key")

    settings = Settings.from_env(env_file)

    assert settings.data_go_kr_service_key == "shell-key"


def test_settings_accept_api_mode_and_relative_database_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATA_MODE=api\nLOCAL_DATABASE_PATH=data/custom.sqlite3\n", encoding="utf-8"
    )
    monkeypatch.delenv("DATA_MODE", raising=False)
    monkeypatch.delenv("LOCAL_DATABASE_PATH", raising=False)

    settings = Settings.from_env(env_file)

    assert settings.data_mode == "api"
    assert settings.local_database_path.name == "custom.sqlite3"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        (name, value)
        for name in ("HTTP_TIMEOUT_SECONDS", "WALKING_SPEED_M_PER_MINUTE")
        for value in ("0", "-1", "nan", "inf", "not-a-number")
    ],
)
def test_settings_reject_invalid_positive_numbers(
    name: str, value: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match=name):
        Settings.from_env(env_file)
