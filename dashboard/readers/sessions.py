"""Reader for Hermes session data from state.db (SQLite, WAL mode, read-only)."""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

HERMES_HOME = Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes'))


def get_db_path() -> Path:
    return HERMES_HOME / 'state.db'


def _connect():
    """Open a read-only SQLite connection. Returns None if DB doesn't exist."""
    db_path = get_db_path()
    if not db_path.exists():
        return None
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def _parse_datetime(value):
    """Convert a unix timestamp (float) or datetime string to a datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OSError):
            return None
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return value


def list_sessions(limit=50, offset=0, search=None) -> list[dict]:
    conn = _connect()
    if conn is None:
        return []
    try:
        if search:
            query = """
                SELECT DISTINCT
                    s.id, s.source, s.model, s.title, s.started_at, s.ended_at,
                    s.message_count, s.tool_call_count, s.input_tokens, s.output_tokens,
                    s.cache_read_tokens, s.reasoning_tokens, s.estimated_cost_usd
                FROM sessions s
                JOIN messages m ON m.session_id = s.id
                JOIN messages_fts ON m.rowid = messages_fts.rowid
                WHERE messages_fts MATCH ?
                ORDER BY s.started_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, (search, limit, offset)).fetchall()
        else:
            query = """
                SELECT
                    id, source, model, title, started_at, ended_at,
                    message_count, tool_call_count, input_tokens, output_tokens,
                    cache_read_tokens, reasoning_tokens, estimated_cost_usd
                FROM sessions
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, (limit, offset)).fetchall()

        results = []
        for row in rows:
            d = _row_to_dict(row)
            d['started_at'] = _parse_datetime(d.get('started_at'))
            d['ended_at'] = _parse_datetime(d.get('ended_at'))
            d['cost'] = d.get('estimated_cost_usd') or 0.0
            results.append(d)
        return results
    finally:
        conn.close()


def get_session(session_id: str) -> dict | None:
    conn = _connect()
    if conn is None:
        return None
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        d = _row_to_dict(row)
        d['started_at'] = _parse_datetime(d.get('started_at'))
        d['ended_at'] = _parse_datetime(d.get('ended_at'))
        d['cost'] = d.get('estimated_cost_usd') or 0.0
        return d
    finally:
        conn.close()


def get_messages(session_id: str) -> list[dict]:
    conn = _connect()
    if conn is None:
        return []
    try:
        query = """
            SELECT id, role, content, tool_call_id, tool_calls, tool_name,
                   timestamp, token_count, finish_reason
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp
        """
        rows = conn.execute(query, (session_id,)).fetchall()
        results = []
        for row in rows:
            d = _row_to_dict(row)
            d['timestamp'] = _parse_datetime(d.get('timestamp'))
            # Ensure content is always a string
            if d.get('content') is None:
                d['content'] = ''
            results.append(d)
        return results
    finally:
        conn.close()


def get_messages_after(session_id: str, after_id: int) -> list[dict]:
    """Get messages with id > after_id for a session. Used by SSE streaming."""
    conn = _connect()
    if conn is None:
        return []
    try:
        query = """
            SELECT id, role, content, tool_call_id, tool_calls, tool_name,
                   timestamp, token_count, finish_reason
            FROM messages
            WHERE session_id = ? AND id > ?
            ORDER BY id
        """
        rows = conn.execute(query, (session_id, after_id)).fetchall()
        results = []
        for row in rows:
            d = _row_to_dict(row)
            d['timestamp'] = _parse_datetime(d.get('timestamp'))
            if d.get('content') is None:
                d['content'] = ''
            results.append(d)
        return results
    finally:
        conn.close()


def get_session_ended(session_id: str) -> bool:
    """Check if a session has ended (ended_at is set)."""
    conn = _connect()
    if conn is None:
        return True
    try:
        row = conn.execute(
            "SELECT ended_at FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return True
        return row['ended_at'] is not None
    finally:
        conn.close()


def get_stats() -> dict:
    conn = _connect()
    if conn is None:
        return {
            'total_sessions': 0,
            'total_cost': 0.0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'models_used': [],
            'platforms_used': [],
        }
    try:
        row = conn.execute("""
            SELECT
                COUNT(*) AS total_sessions,
                COALESCE(SUM(estimated_cost_usd), 0.0) AS total_cost,
                COALESCE(SUM(input_tokens), 0) AS total_input_tokens,
                COALESCE(SUM(output_tokens), 0) AS total_output_tokens
            FROM sessions
        """).fetchone()

        models = conn.execute("SELECT DISTINCT model FROM sessions WHERE model IS NOT NULL").fetchall()
        platforms = conn.execute("SELECT DISTINCT source FROM sessions WHERE source IS NOT NULL").fetchall()

        return {
            'total_sessions': row['total_sessions'],
            'total_cost': row['total_cost'],
            'total_input_tokens': row['total_input_tokens'],
            'total_output_tokens': row['total_output_tokens'],
            'models_used': [r['model'] for r in models],
            'platforms_used': [r['source'] for r in platforms],
        }
    finally:
        conn.close()
