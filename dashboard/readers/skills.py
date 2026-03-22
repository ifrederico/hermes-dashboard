"""Read-only access to Hermes skills (~/.hermes/skills/)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from dashboard.config import skills_dir


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    category: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    platforms: list[str] = field(default_factory=list)
    body: str = ""
    frontmatter: dict = field(default_factory=dict)
    linked_files: dict = field(default_factory=dict)


def _parse_skill(skill_md_path: Path, base_dir: Path) -> Optional[Skill]:
    """Parse a SKILL.md file into a Skill object."""
    try:
        text = skill_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    # Split YAML frontmatter from body
    frontmatter = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                frontmatter = {}
            body = parts[2].strip()

    name = frontmatter.get("name", skill_md_path.parent.name)
    description = frontmatter.get("description", "")

    # Infer category from path depth
    rel = skill_md_path.parent.relative_to(base_dir)
    parts = rel.parts
    category = parts[0] if len(parts) > 1 else None

    # Find linked files
    linked = {}
    for subdir in ("references", "templates", "scripts", "assets"):
        d = skill_md_path.parent / subdir
        if d.is_dir():
            linked[subdir] = sorted([f.name for f in d.iterdir() if f.is_file()])

    return Skill(
        name=name,
        description=description,
        path=skill_md_path.parent,
        category=category,
        version=frontmatter.get("version"),
        author=frontmatter.get("author"),
        platforms=frontmatter.get("platforms", []),
        body=body,
        frontmatter=frontmatter,
        linked_files=linked,
    )


def list_skills() -> list[Skill]:
    """Walk the skills directory and return all skills."""
    base = skills_dir()
    if not base.exists():
        return []

    skills = []
    for skill_md in sorted(base.rglob("SKILL.md")):
        skill = _parse_skill(skill_md, base)
        if skill:
            skills.append(skill)

    return skills


def get_skill(name: str) -> Optional[Skill]:
    """Find a skill by name."""
    for skill in list_skills():
        if skill.name == name:
            return skill
    return None


def get_skill_file(name: str, file_path: str) -> Optional[str]:
    """Read a linked file from a skill directory."""
    skill = get_skill(name)
    if not skill:
        return None
    target = skill.path / file_path
    if not target.exists() or not target.is_file():
        return None
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
