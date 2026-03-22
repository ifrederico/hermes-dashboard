"""Read-only access to Hermes memory files (MEMORY.md + USER.md)."""

from dataclasses import dataclass
from pathlib import Path

from dashboard.config import memories_dir


@dataclass
class MemoryStore:
    entries: list[str]
    raw: str
    file_path: Path
    exists: bool


def _read_memory_file(path: Path) -> MemoryStore:
    """Read a §-delimited memory file."""
    if not path.exists():
        return MemoryStore(entries=[], raw="", file_path=path, exists=False)

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return MemoryStore(entries=[], raw="", file_path=path, exists=True)

    entries = [e.strip() for e in raw.split("\n§\n") if e.strip()]
    return MemoryStore(entries=entries, raw=raw, file_path=path, exists=True)


def get_memory() -> MemoryStore:
    """Read agent memory (MEMORY.md)."""
    return _read_memory_file(memories_dir() / "MEMORY.md")


def get_user_profile() -> MemoryStore:
    """Read user profile (USER.md)."""
    return _read_memory_file(memories_dir() / "USER.md")


def save_memory(raw: str) -> None:
    """Write agent memory (MEMORY.md)."""
    path = memories_dir() / "MEMORY.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw.rstrip() + "\n", encoding="utf-8")


def save_user_profile(raw: str) -> None:
    """Write user profile (USER.md)."""
    path = memories_dir() / "USER.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw.rstrip() + "\n", encoding="utf-8")
