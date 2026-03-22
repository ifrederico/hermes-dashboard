"""Reader for Hermes skill files (SKILL.md with YAML frontmatter)."""

import os
from pathlib import Path

import yaml

HERMES_HOME = Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes'))

SKILLS_DIR = HERMES_HOME / 'skills'

LINKED_SUBDIRS = ('references', 'templates', 'scripts', 'assets')


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a markdown file.

    Returns (metadata_dict, body_text). If no frontmatter found,
    returns ({}, full_text).
    """
    if not text.startswith('---'):
        return {}, text

    parts = text.split('---', 2)
    if len(parts) < 3:
        return {}, text

    # parts[0] is empty (before first ---), parts[1] is YAML, parts[2] is body
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}

    body = parts[2].strip()
    return meta, body


def _infer_category(skill_path: Path) -> str:
    """Infer category from directory structure relative to skills dir."""
    try:
        rel = skill_path.parent.relative_to(SKILLS_DIR)
    except ValueError:
        return ''
    # If SKILL.md is directly in skills/, no category
    parts = rel.parts
    if not parts:
        return ''
    # Use the top-level parent directory as category
    return parts[0]


def _collect_linked_files(skill_dir: Path) -> list[str]:
    """List files in linked subdirectories (references/, templates/, scripts/, assets/)."""
    files = []
    for subdir_name in LINKED_SUBDIRS:
        subdir = skill_dir / subdir_name
        if subdir.is_dir():
            for f in sorted(subdir.rglob('*')):
                if f.is_file():
                    try:
                        files.append(str(f.relative_to(skill_dir)))
                    except ValueError:
                        files.append(str(f))
    return files


def list_skills() -> list[dict]:
    if not SKILLS_DIR.is_dir():
        return []

    skills = []
    for skill_file in SKILLS_DIR.rglob('SKILL.md'):
        try:
            text = skill_file.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue

        meta, _ = _parse_frontmatter(text)
        category = _infer_category(skill_file)

        skills.append({
            'name': meta.get('name', skill_file.parent.name),
            'description': meta.get('description', ''),
            'version': meta.get('version', ''),
            'category': category,
            'path': str(skill_file),
        })

    skills.sort(key=lambda s: (s['category'], s['name']))
    return skills


def get_skill(name: str) -> dict | None:
    if not SKILLS_DIR.is_dir():
        return None

    for skill_file in SKILLS_DIR.rglob('SKILL.md'):
        try:
            text = skill_file.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue

        meta, body = _parse_frontmatter(text)
        skill_name = meta.get('name', skill_file.parent.name)

        if skill_name == name:
            category = _infer_category(skill_file)
            linked_files = _collect_linked_files(skill_file.parent)

            return {
                'name': skill_name,
                'description': meta.get('description', ''),
                'version': meta.get('version', ''),
                'category': category,
                'body': body,
                'path': str(skill_file),
                'linked_files': linked_files,
            }

    return None
