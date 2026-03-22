# ☤ Hermes Dashboard

A minimal, read-only web dashboard for [Hermes Agent](https://github.com/ifrederico/hermes-agent). Reads `~/.hermes/` data files and renders them in a clean, bearblog-inspired web UI.

Zero coupling to the Hermes codebase — just reads the same files.

## Features

- **Session browser** — paginated list with FTS5 search, full message viewer
- **Memory viewer** — agent memory and user profile entries side-by-side
- **Skill browser** — skills grouped by category, rendered markdown detail pages
- **Overview dashboard** — aggregate stats (sessions, tokens, cost, models, platforms)
- **Dark mode** — automatic via `prefers-color-scheme`
- **No JavaScript framework** — vanilla HTML/CSS, Jinja2 templates

## Install

```bash
pip install hermes-dashboard
```

Or from source:

```bash
git clone https://github.com/ifrederico/hermes-dashboard
cd hermes-dashboard
pip install -e .
```

## Usage

```bash
# Default: http://127.0.0.1:9191
hermes-dashboard

# Custom port
hermes-dashboard --port 8080

# Custom hermes home
HERMES_HOME=/path/to/hermes hermes-dashboard

# Development mode with auto-reload
hermes-dashboard --reload
```

Or as a module:

```bash
python -m dashboard --port 9191
```

## Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Framework | Starlette | Lightweight ASGI, no auto-docs overhead |
| Templates | Jinja2 | Same pattern as bearblog |
| Server | uvicorn | Standard ASGI server |
| CSS | ~700 lines, hand-written | CSS variables, auto dark mode |
| JS | None | Zero JavaScript required |

Total dependencies: starlette, jinja2, uvicorn, pyyaml, markdown, pygments.

## Data Sources (read-only)

| Source | Location | Format |
|--------|----------|--------|
| Sessions | `~/.hermes/state.db` | SQLite (WAL mode) |
| Memory | `~/.hermes/memories/MEMORY.md` | Text (§-delimited) |
| User Profile | `~/.hermes/memories/USER.md` | Text (§-delimited) |
| Skills | `~/.hermes/skills/*/SKILL.md` | YAML frontmatter + Markdown |

All paths respect the `HERMES_HOME` environment variable (default: `~/.hermes`).

## Pages

| Route | Page |
|-------|------|
| `GET /` | Overview — stats, recent sessions |
| `GET /sessions` | Session list with search |
| `GET /sessions/{id}` | Session detail — full message thread |
| `GET /memory` | Memory + user profile entries |
| `GET /skills` | Skills grouped by category |
| `GET /skills/{name}` | Skill detail — rendered markdown |

## Design Principles

1. **Read-only** — never writes to Hermes data files
2. **Zero config** — finds `~/.hermes/` automatically
3. **No build step** — no npm, no webpack, no TypeScript
4. **Minimal dependencies** — 6 packages total
5. **Localhost only** — binds to 127.0.0.1 by default

## Roadmap

- [ ] Cron job viewer (jobs.json + output history)
- [ ] Config viewer (redacted secrets)
- [ ] Error log tail with auto-refresh
- [ ] Usage analytics (cost over time, tokens by model)
- [ ] JSON API endpoint for programmatic access

## License

MIT
