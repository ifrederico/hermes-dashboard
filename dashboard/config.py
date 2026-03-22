"""Dashboard configuration — resolves HERMES_HOME and data paths."""

import os
from pathlib import Path


def hermes_home() -> Path:
    """Resolve the Hermes data directory."""
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def state_db_path() -> Path:
    return hermes_home() / "state.db"


def memories_dir() -> Path:
    return hermes_home() / "memories"


def skills_dir() -> Path:
    return hermes_home() / "skills"


def cron_dir() -> Path:
    return hermes_home() / "cron"


def config_yaml_path() -> Path:
    return hermes_home() / "config.yaml"


def logs_dir() -> Path:
    return hermes_home() / "logs"
