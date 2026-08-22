"""Runtime configuration for public-data clients."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from dotenv import load_dotenv

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_DATABASE_FILE = Path(__file__).resolve().parents[1] / "data/processed/gyeongbuk.sqlite3"
DataMode = Literal["file", "api"]


@dataclass(frozen=True, slots=True)
class Settings:
    """Environment-backed application settings."""

    data_go_kr_service_key: str | None
    http_timeout_seconds: float = 10.0
    walking_speed_m_per_minute: float = 60.0
    data_mode: DataMode = "file"
    local_database_path: Path = DEFAULT_DATABASE_FILE

    @classmethod
    def from_env(cls, env_file: str | Path = DEFAULT_ENV_FILE) -> Settings:
        """Load dotenv defaults without overriding shell or CI variables."""

        load_dotenv(dotenv_path=env_file, override=False)
        key = os.getenv("DATA_GO_KR_SERVICE_KEY")
        timeout = _positive_float("HTTP_TIMEOUT_SECONDS", "10")
        walking_speed = _positive_float("WALKING_SPEED_M_PER_MINUTE", "60")
        raw_mode = os.getenv("DATA_MODE", "file").strip().lower()
        if raw_mode not in {"file", "api"}:
            raise ValueError("DATA_MODE must be either 'file' or 'api'")
        raw_database = os.getenv("LOCAL_DATABASE_PATH")
        database_path = Path(raw_database).expanduser() if raw_database else DEFAULT_DATABASE_FILE
        if not database_path.is_absolute():
            database_path = Path(__file__).resolve().parents[1] / database_path
        return cls(
            data_go_kr_service_key=key.strip() if key and key.strip() else None,
            http_timeout_seconds=timeout,
            walking_speed_m_per_minute=walking_speed,
            data_mode=cast(DataMode, raw_mode),
            local_database_path=database_path,
        )


def _positive_float(name: str, default: str) -> float:
    raw = os.getenv(name, default)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a finite positive number") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return value
