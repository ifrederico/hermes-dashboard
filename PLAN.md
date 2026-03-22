# Hermes Dashboard — Project Plan

## What Is This

A standalone, read-only web dashboard for [Hermes Agent](https://github.com/ifrederico/hermes-agent). It reads `~/.hermes/` data files (SQLite, JSON, YAML, Markdown) and renders them in a minimal, bearblog-style web UI. Zero coupling to the Hermes codebase — just reads the same files.

## Where It Lives

```
~/github/hermes-dashboard/       ← standalone repo
```

Separate repo, separate package, separate release cycle. `pip install hermes-dashboard` and run.

## Stack

- **Python 3.11+** (matches Hermes requirement)
- **Starlette** — lightweight ASGI framework (FastAPI without the auto-docs overhead)
- **Jinja2** — HTML templating (same as bearblog pattern)
- **uvicorn** — ASGI server
- **No JavaScript framework** — vanilla JS only, Chart.js from CDN for graphs
- **~400 lines of CSS** — CSS variables, automatic dark mode, bearblog-inspired

Total new dependencies: starlette, jinja2, uvicorn (3 packages).

## Data Sources (all read-only)

| Source | Location | Format | Dashboard Use |
|--------|----------|--------|---------------|
| Sessions | `~/.hermes/state.db` | SQLite (WAL) | Session list, message viewer, search |
| Memory | `~/.hermes/memories/MEMORY.md` | Text (§-delimited) | Memory entries viewer |
| User Profile | `~/.hermes/memories/USER.md` | Text (§-delimited) | User profile viewer |
| Skills | `~/.hermes/skills/*/SKILL.md` | YAML frontmatter + MD | Skill browser |
| Cron Jobs | `~/.hermes/cron/jobs.json` | JSON | Job status, history |
| Cron Output | `~/.hermes/cron/output/*/` | Markdown files | Job output viewer |
| Config | `~/.hermes/config.yaml` | YAML | Config viewer |
| Logs | `~/.hermes/logs/errors.log` | Text | Error log viewer |

All paths respect `HERMES_HOME` env var (default: `~/.hermes`).

---

## Project Structure

```
hermes-dashboard/
├── PLAN.md
├── README.md
├── LICENSE
├── pyproject.toml
├── dashboard/
│   ├── __init__.py
│   ├── app.py                  # Starlette app, routes, startup
│   ├── __main__.py             # `python -m dashboard` entry point
│   ├── config.py               # HERMES_HOME resolution, dashboard settings
│   ├── readers/                # Read-only data access layer
│   │   ├── __init__.py
│   │   ├── sessions.py         # SQLite reader for state.db
│   │   ├── memory.py           # MEMORY.md + USER.md parser
│   │   ├── skills.py           # Skills directory walker + frontmatter parser
│   │   ├── cron.py             # jobs.json + output reader
│   │   └── config.py           # config.yaml parser
│   ├── templates/              # Jinja2 templates
│   │   ├── base.html           # Layout, nav, CSS variables
│   │   ├── index.html          # Dashboard home / overview
│   │   ├── sessions.html       # Session list with search
│   │   ├── session_detail.html # Single session message viewer
│   │   ├── memory.html         # Memory + user profile
│   │   ├── skills.html         # Skill browser
│   │   ├── skill_detail.html   # Single skill viewer (rendered markdown)
│   │   ├── cron.html           # Cron job list + status
│   │   ├── cron_detail.html    # Single job + output history
│   │   ├── config.html         # Config viewer
│   │   └── logs.html           # Error log viewer
│   └── static/
│       ├── style.css           # ~400 lines, bearblog-inspired
│       └── hermes.svg          # Logo/favicon
```

---

## Pages & Routes

### Phase 1 — Core (MVP)

| Route | Page | What It Shows |
|-------|------|---------------|
| `GET /` | Overview | Stats summary: session count, total cost, active cron jobs, skill count |
| `GET /sessions` | Sessions | Paginated list, sortable by date/cost/tokens. Search via FTS5 |
| `GET /sessions/{id}` | Session Detail | Full message thread, token counts, cost, model used |
| `GET /memory` | Memory | Both MEMORY.md and USER.md entries, displayed as cards |
| `GET /skills` | Skills | Grid/list of all skills with name, description, category |
| `GET /skills/{name}` | Skill Detail | Rendered SKILL.md markdown, metadata, linked files |

### Phase 2 — Operations

| Route | Page | What It Shows |
|-------|------|---------------|
| `GET /cron` | Cron Jobs | Job list with status badges, next run, last status |
| `GET /cron/{id}` | Cron Detail | Job config, run history, output viewer |
| `GET /config` | Config | Rendered config.yaml (secrets redacted) |
| `GET /logs` | Logs | Tail of errors.log with auto-refresh |

### Phase 3 — Analytics

| Route | Page | What It Shows |
|-------|------|---------------|
| `GET /analytics` | Usage Analytics | Cost over time, tokens by model, sessions by platform |
| `GET /api/stats` | JSON API | Raw stats endpoint for custom integrations |

---

## Implementation Phases

### Phase 1: Foundation + Core Pages
*Target: Working dashboard you can actually use*

1. **Project scaffold**
   - pyproject.toml with starlette, jinja2, uvicorn, pyyaml, markdown
   - Entry points: `hermes-dashboard` CLI command + `python -m dashboard`
   - HERMES_HOME resolution logic

2. **Readers layer**
   - `sessions.py` — open state.db read-only, list sessions, get messages, FTS search
   - `memory.py` — read and parse §-delimited memory files
   - `skills.py` — walk skills dir, parse YAML frontmatter, render markdown

3. **Templates + CSS**
   - `base.html` — nav sidebar, CSS variables, dark mode, responsive
   - `style.css` — bearblog-inspired, ~400 lines max
   - Session list, session detail, memory, skills pages

4. **Starlette app**
   - Mount static files, configure Jinja2
   - Route handlers that call readers and render templates
   - Error pages (404, 500)

### Phase 2: Operations Pages
*Target: Monitor your agent's background work*

5. **Cron reader + pages**
   - Parse jobs.json, list output files
   - Job status badges, output viewer with markdown rendering

6. **Config + logs**
   - Config viewer with secret redaction
   - Log tail with optional auto-refresh (vanilla JS polling)

### Phase 3: Analytics
*Target: Understand your usage patterns*

7. **Analytics page**
   - Cost tracking over time (Chart.js bar chart, like bearblog analytics)
   - Token usage by model
   - Sessions by platform (cli vs telegram vs discord)
   - Aggregate stats

8. **JSON API**
   - `/api/stats` endpoint for programmatic access
   - Simple JSON responses, no auth needed (localhost only)

---

## Design Principles

1. **Read-only** — the dashboard never writes to Hermes data files. View only.
2. **Zero config** — finds `~/.hermes/` automatically, works out of the box.
3. **No build step** — no npm, no webpack, no TypeScript. Python + HTML + CSS.
4. **Minimal dependencies** — starlette, jinja2, uvicorn, pyyaml, markdown. That's it.
5. **Bearblog aesthetic** — clean, fast, content-focused. CSS variables for theming.
6. **Dark mode** — automatic via `prefers-color-scheme`, like bearblog.
7. **Localhost only** — binds to 127.0.0.1 by default. Not a production web app.

## CSS Theme (bearblog-derived)

```css
:root {
    --width: 900px;
    --font-main: "Berkeley Mono", "SF Mono", monospace;
    --font-secondary: system-ui, sans-serif;
    --bg: #fafafa;
    --text: #333;
    --text-dim: #777;
    --heading: #111;
    --link: #3273dc;
    --accent: #d4a017;        /* hermes gold */
    --surface: #f0f0f0;
    --border: #e0e0e0;
    --code-bg: #f5f5f5;
}

@media (prefers-color-scheme: dark) {
    :root {
        --bg: #0a0a0a;
        --text: #ccc;
        --text-dim: #888;
        --heading: #eee;
        --link: #8cc2dd;
        --accent: #d4a017;
        --surface: #1a1a1a;
        --border: #333;
        --code-bg: #111;
    }
}
```

## Running

```bash
# Install
pip install hermes-dashboard

# Run (default: http://127.0.0.1:9191)
hermes-dashboard

# Custom port
hermes-dashboard --port 8080

# Custom hermes home
HERMES_HOME=/path/to/hermes hermes-dashboard

# Or as a module
python -m dashboard --port 9191
```

## Future Possibilities (not in scope now)

- Write operations (edit memory, toggle cron jobs, update config)
- WebSocket for live session streaming
- Auth layer for remote access
- Hermes CLI integration (`hermes dashboard` command)
- Plugin system for custom pages
