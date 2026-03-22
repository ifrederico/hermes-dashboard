"""Reader for Hermes memory files (MEMORY.md and USER.md)."""

import os
from pathlib import Path

HERMES_HOME = Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes'))

DELIMITER = '\n§\n'


def _read_entries(filepath: Path) -> list[str]:
    """Read a memory file and split by the § delimiter. Returns empty list if missing."""
    if not filepath.exists():
        return []
    try:
        text = filepath.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    if not text.strip():
        return []
    entries = text.split(DELIMITER)
    return [e.strip() for e in entries if e.strip()]


def get_memory_entries() -> list[str]:
    return _read_entries(HERMES_HOME / 'memories' / 'MEMORY.md')


def get_user_entries() -> list[str]:
    return _read_entries(HERMES_HOME / 'memories' / 'USER.md')


def get_all() -> dict:
    return {
        'memory': get_memory_entries(),
        'user': get_user_entries(),
    }
