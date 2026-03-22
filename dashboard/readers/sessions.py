"""Read-only access to Hermes sessions in state.db (SQLite, WAL mode)."""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dashboard.config import state_db_path


@dataclass
class Session:
    id: str
    source: str
    model: Optional[str]
    parent_session_id: Optional[str]
    started_at: float
    ended_at: Optional[float]
    end_reason: Optional[str]
    message_count: int
    tool_call_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    reasoning_tokens: int
    estimated_cost_usd: Optional[float]
    title: Optional[str]
    is_subagent: bool = False

    @property
    def started(self) -> datetime:
        return datetime.fromtimestamp(self.started_at, tz=timezone.utc)

    @property
    def ended(self) -> Optional[datetime]:
        return datetime.fromtimestamp(self.ended_at, tz=timezone.utc) if self.ended_at else None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.ended_at and self.started_at:
            return self.ended_at - self.started_at
        return None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def short_id(self) -> str:
        return self.id[:20] if len(self.id) > 20 else self.id

    @property
    def model_short(self) -> str:
        if not self.model:
            return "—"
        # "anthropic/claude-opus-4.6" → "claude-opus-4.6"
        return self.model.split("/", 1)[-1] if "/" in self.model else self.model


@dataclass
class Message:
    id: int
    session_id: str
    role: str
    content: Optional[str]
    tool_call_id: Optional[str]
    tool_calls: Optional[str]
    tool_name: Optional[str]
    timestamp: float
    token_count: Optional[int]

    @property
    def time(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)

    @property
    def content_preview(self) -> str:
        if not self.content:
            return ""
        text = self.content[:200].replace("\n", " ")
        return text


def _connect() -> sqlite3.Connection:
    db = state_db_path()
    if not db.exists():
        raise FileNotFoundError(f"Hermes state.db not found at {db}")
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _detect_subagents(sessions: list[Session]) -> list[Session]:
    """Mark sessions that look like subagent runs.

    Heuristic: a CLI session with no parent_session_id whose start time falls
    within the time range of a conversation chain. Also skips cron sessions
    (they have their own badge).
    """
    conn = _connect()
    try:
        # Find ALL chained session IDs and their time ranges from the DB
        # (not just the ones in the current page)
        rows = conn.execute("""
            SELECT id, parent_session_id, started_at, ended_at
            FROM sessions
            WHERE parent_session_id IS NOT NULL
               OR id IN (SELECT parent_session_id FROM sessions WHERE parent_session_id IS NOT NULL)
        """).fetchall()

        chained_ids = set()
        chain_ranges = []  # (start, end) of each conversation chain

        # Collect all chained IDs
        for r in rows:
            chained_ids.add(r["id"])

        # Find roots (sessions that are parents but have no parent themselves)
        roots = [r for r in rows if not r["parent_session_id"]
                 and r["id"] in {row["parent_session_id"] for row in rows if row["parent_session_id"]}]

        for root in roots:
            # Walk chain to find full time span
            chain_start = root["started_at"]
            chain_end = root["ended_at"] or (root["started_at"] + 86400)
            current = root["id"]
            seen = {current}
            while True:
                child = None
                for r in rows:
                    if r["parent_session_id"] == current and r["id"] not in seen:
                        child = r
                        break
                if not child:
                    break
                seen.add(child["id"])
                chain_end = child["ended_at"] or (child["started_at"] + 86400)
                current = child["id"]
            chain_ranges.append((chain_start, chain_end))

        # Mark orphan CLI sessions that fall within chain time ranges
        for s in sessions:
            if s.id in chained_ids:
                continue
            if s.source == "cron" or s.source != "cli":
                continue
            if s.parent_session_id:
                continue
            for (c_start, c_end) in chain_ranges:
                if c_start <= s.started_at <= c_end:
                    s.is_subagent = True
                    break

        return sessions
    finally:
        conn.close()


def list_sessions(limit: int = 50, offset: int = 0, include_subagents: bool = True) -> tuple[list[Session], int]:
    """List sessions, newest first. Returns (sessions, total_count)."""
    conn = _connect()
    try:
        # Total count
        row = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()
        total = row["c"]

        rows = conn.execute("""
            SELECT id, source, model, parent_session_id, started_at, ended_at,
                   end_reason, message_count, tool_call_count, input_tokens,
                   output_tokens, cache_read_tokens, cache_write_tokens,
                   reasoning_tokens, estimated_cost_usd, title
            FROM sessions
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()

        sessions = [Session(**dict(r)) for r in rows]
        sessions = _detect_subagents(sessions)

        if not include_subagents:
            sessions = [s for s in sessions if not s.is_subagent]

        return sessions, total
    finally:
        conn.close()


def get_session(session_id: str) -> Optional[Session]:
    """Get a single session by ID."""
    conn = _connect()
    try:
        row = conn.execute("""
            SELECT id, source, model, parent_session_id, started_at, ended_at,
                   end_reason, message_count, tool_call_count, input_tokens,
                   output_tokens, cache_read_tokens, cache_write_tokens,
                   reasoning_tokens, estimated_cost_usd, title
            FROM sessions WHERE id = ?
        """, (session_id,)).fetchone()
        return Session(**dict(row)) if row else None
    finally:
        conn.close()


def get_conversation_chain(session_id: str) -> list[Session]:
    """Walk parent_session_id links to reconstruct a full conversation chain."""
    conn = _connect()
    try:
        # Walk up to find root
        current = session_id
        root = current
        seen = set()
        while current and current not in seen:
            seen.add(current)
            row = conn.execute(
                "SELECT parent_session_id FROM sessions WHERE id = ?", (current,)
            ).fetchone()
            if row and row["parent_session_id"]:
                root = row["parent_session_id"]
                current = root
            else:
                break

        # Walk down from root
        chain = []
        current = root
        seen = set()
        while current and current not in seen:
            seen.add(current)
            row = conn.execute("""
                SELECT id, source, model, parent_session_id, started_at, ended_at,
                       end_reason, message_count, tool_call_count, input_tokens,
                       output_tokens, cache_read_tokens, cache_write_tokens,
                       reasoning_tokens, estimated_cost_usd, title
                FROM sessions WHERE id = ?
            """, (current,)).fetchone()
            if row:
                chain.append(Session(**dict(row)))
            # Find child
            child = conn.execute(
                "SELECT id FROM sessions WHERE parent_session_id = ?", (current,)
            ).fetchone()
            current = child["id"] if child else None

        return chain
    finally:
        conn.close()


def get_messages(session_id: str) -> list[Message]:
    """Get all messages for a session, ordered by timestamp."""
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT id, session_id, role, content, tool_call_id, tool_calls,
                   tool_name, timestamp, token_count
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC, id ASC
        """, (session_id,)).fetchall()
        return [Message(**dict(r)) for r in rows]
    finally:
        conn.close()


def search_sessions(query: str, limit: int = 20) -> list[Session]:
    """Full-text search across message content, returns matching sessions."""
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT DISTINCT s.id, s.source, s.model, s.parent_session_id,
                   s.started_at, s.ended_at, s.end_reason, s.message_count,
                   s.tool_call_count, s.input_tokens, s.output_tokens,
                   s.cache_read_tokens, s.cache_write_tokens, s.reasoning_tokens,
                   s.estimated_cost_usd, s.title
            FROM messages_fts fts
            JOIN messages m ON m.rowid = fts.rowid
            JOIN sessions s ON s.id = m.session_id
            WHERE messages_fts MATCH ?
            ORDER BY s.started_at DESC
            LIMIT ?
        """, (query, limit)).fetchall()
        sessions = [Session(**dict(r)) for r in rows]
        return _detect_subagents(sessions)
    finally:
        conn.close()


def get_stats() -> dict:
    """Aggregate stats for the overview page."""
    conn = _connect()
    try:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_sessions,
                SUM(message_count) as total_messages,
                SUM(tool_call_count) as total_tool_calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(estimated_cost_usd) as total_cost,
                MIN(started_at) as first_session,
                MAX(started_at) as last_session
            FROM sessions
        """).fetchone()

        sources = conn.execute("""
            SELECT source, COUNT(*) as count
            FROM sessions
            GROUP BY source
            ORDER BY count DESC
        """).fetchall()

        models = conn.execute("""
            SELECT model, COUNT(*) as count
            FROM sessions
            WHERE model IS NOT NULL
            GROUP BY model
            ORDER BY count DESC
        """).fetchall()

        return {
            "total_sessions": row["total_sessions"] or 0,
            "total_messages": row["total_messages"] or 0,
            "total_tool_calls": row["total_tool_calls"] or 0,
            "total_input_tokens": row["total_input_tokens"] or 0,
            "total_output_tokens": row["total_output_tokens"] or 0,
            "total_cost": row["total_cost"] or 0.0,
            "first_session": row["first_session"],
            "last_session": row["last_session"],
            "sources": {r["source"]: r["count"] for r in sources},
            "models": {r["model"]: r["count"] for r in models},
        }
    finally:
        conn.close()
