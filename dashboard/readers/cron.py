"""Read-only access to Hermes cron jobs (~/.hermes/cron/)."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dashboard.config import cron_dir


@dataclass
class CronJob:
    id: str
    name: str
    prompt: str
    schedule: dict
    schedule_display: str
    state: str
    enabled: bool
    repeat: dict
    skills: list[str]
    model: Optional[str]
    deliver: Optional[str]
    created_at: Optional[str]
    next_run_at: Optional[str]
    last_run_at: Optional[str]
    last_status: Optional[str]
    last_error: Optional[str]
    origin: Optional[dict] = None
    raw: dict = field(default_factory=dict)


def list_jobs() -> list[CronJob]:
    """Read all cron jobs from jobs.json."""
    jobs_file = cron_dir() / "jobs.json"
    if not jobs_file.exists():
        return []

    try:
        data = json.loads(jobs_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    jobs = []
    for j in data.get("jobs", []):
        jobs.append(CronJob(
            id=j.get("id", ""),
            name=j.get("name", ""),
            prompt=j.get("prompt", ""),
            schedule=j.get("schedule", {}),
            schedule_display=j.get("schedule", {}).get("display", ""),
            state=j.get("state", "unknown"),
            enabled=j.get("enabled", False),
            repeat=j.get("repeat", {}),
            skills=j.get("skills", []) or ([j["skill"]] if j.get("skill") else []),
            model=j.get("model"),
            deliver=j.get("deliver"),
            created_at=j.get("created_at"),
            next_run_at=j.get("next_run_at"),
            last_run_at=j.get("last_run_at"),
            last_status=j.get("last_status"),
            last_error=j.get("last_error"),
            origin=j.get("origin"),
            raw=j,
        ))

    return jobs


def get_job(job_id: str) -> Optional[CronJob]:
    """Get a single cron job by ID."""
    for job in list_jobs():
        if job.id == job_id:
            return job
    return None


def get_job_outputs(job_id: str) -> list[dict]:
    """List output files for a cron job, newest first."""
    output_dir = cron_dir() / "output" / job_id
    if not output_dir.exists():
        return []

    outputs = []
    for f in sorted(output_dir.glob("*.md"), reverse=True):
        try:
            content = f.read_text(encoding="utf-8")
            outputs.append({
                "filename": f.name,
                "timestamp": f.stem,
                "content": content,
            })
        except (OSError, UnicodeDecodeError):
            continue

    return outputs
