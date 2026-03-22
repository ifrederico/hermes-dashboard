"""Read-only access to Hermes config.yaml."""

from pathlib import Path
from typing import Any

import yaml

from dashboard.config import config_yaml_path


# Keys whose values should be redacted in the UI
_SECRET_PATTERNS = {
    "api_key", "secret", "token", "password", "webhook_url",
    "bot_token", "client_secret",
}


def read_config() -> dict[str, Any]:
    """Read config.yaml and return as dict."""
    path = config_yaml_path()
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return {}


def read_config_redacted() -> dict[str, Any]:
    """Read config.yaml with secret values replaced by '••••••••'."""
    config = read_config()
    return _redact(config)


def _redact(obj: Any, key: str = "") -> Any:
    if isinstance(obj, dict):
        return {k: _redact(v, k) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_redact(item, key) for item in obj]
    elif isinstance(obj, str) and any(p in key.lower() for p in _SECRET_PATTERNS):
        return "••••••••" if obj else ""
    return obj
