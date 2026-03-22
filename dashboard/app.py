"""Hermes Dashboard — Starlette application."""

from pathlib import Path
from collections import defaultdict
from datetime import datetime

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import markdown
import pygments
from pygments.formatters import HtmlFormatter

from dashboard.readers import sessions, memory, skills

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── Jinja2 custom filters ────────────────────────────────────────


def intcomma(value):
    """Format number with commas: 1234567 -> 1,234,567."""
    try:
        n = int(value)
        return f"{n:,}"
    except (ValueError, TypeError):
        return value


def short_number(value):
    """Compact number: 1234567 -> 1.2M."""
    try:
        n = float(value)
    except (ValueError, TypeError):
        return value
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def format_cost(value):
    """Format USD cost: 0.0234 -> $0.0234."""
    try:
        v = float(value)
        if v == 0:
            return "—"
        if v < 0.01:
            return f"${v:.4f}"
        return f"${v:.2f}"
    except (ValueError, TypeError):
        return "—"


def format_date(value, fmt="%Y-%m-%d %H:%M"):
    """Format datetime object or timestamp."""
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value)
    if isinstance(value, datetime):
        return value.strftime(fmt)
    return str(value)


def short_model(value):
    """Shorten model name: anthropic/claude-opus-4.6 -> claude-opus-4.6."""
    if not value:
        return "—"
    if "/" in value:
        return value.split("/", 1)[1]
    return value


def render_markdown(text):
    """Render markdown to HTML."""
    if not text:
        return ""
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "codehilite", "nl2br"],
        extension_configs={
            "codehilite": {"css_class": "highlight", "guess_lang": False}
        },
    )


# Register filters
templates.env.filters["intcomma"] = intcomma
templates.env.filters["short_number"] = short_number
templates.env.filters["format_cost"] = format_cost
templates.env.filters["format_date"] = format_date
templates.env.filters["short_model"] = short_model
templates.env.filters["render_markdown"] = render_markdown


# ── Route handlers ────────────────────────────────────────────────


async def index(request: Request) -> Response:
    stats = sessions.get_stats()
    recent = sessions.list_sessions(limit=10, offset=0)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"stats": stats, "recent_sessions": recent},
    )


async def sessions_list(request: Request) -> Response:
    query = request.query_params.get("q", "").strip()
    page = int(request.query_params.get("page", 1))
    per_page = 30
    offset = (page - 1) * per_page

    results = sessions.list_sessions(
        limit=per_page + 1,  # fetch one extra to check has_next
        offset=offset,
        search=query or None,
    )

    has_next = len(results) > per_page
    if has_next:
        results = results[:per_page]

    return templates.TemplateResponse(
        request,
        "sessions.html",
        {
            "sessions": results,
            "query": query,
            "page": page,
            "has_next": has_next,
        },
    )


async def session_detail(request: Request) -> Response:
    session_id = request.path_params["session_id"]
    session = sessions.get_session(session_id)
    if not session:
        return templates.TemplateResponse(request, "404.html", status_code=404)

    msgs = sessions.get_messages(session_id)
    return templates.TemplateResponse(
        request,
        "session_detail.html",
        {"session": session, "messages": msgs},
    )


async def memory_page(request: Request) -> Response:
    data = memory.get_all()
    return templates.TemplateResponse(
        request,
        "memory.html",
        {
            "memory_entries": data["memory"],
            "user_entries": data["user"],
        },
    )


async def skills_list(request: Request) -> Response:
    all_skills = skills.list_skills()
    by_category = defaultdict(list)
    for s in all_skills:
        cat = s.get("category") or "uncategorized"
        by_category[cat].append(s)
    # Sort categories
    by_category = dict(sorted(by_category.items()))
    return templates.TemplateResponse(
        request,
        "skills.html",
        {"skills_by_category": by_category},
    )


async def skill_detail_page(request: Request) -> Response:
    name = request.path_params["name"]
    skill = skills.get_skill(name)
    if not skill:
        return templates.TemplateResponse(request, "404.html", status_code=404)

    # Pre-render markdown body
    skill["body_html"] = render_markdown(skill.get("body", ""))
    return templates.TemplateResponse(
        request,
        "skill_detail.html",
        {"skill": skill},
    )


async def not_found(request: Request, exc: Exception) -> Response:
    return templates.TemplateResponse(request, "404.html", status_code=404)


async def server_error(request: Request, exc: Exception) -> Response:
    return templates.TemplateResponse(
        request,
        "404.html",
        {"message": "Internal server error"},
        status_code=500,
    )


# ── App ────────────────────────────────────────────────────────────

routes = [
    Route("/", index),
    Route("/sessions", sessions_list),
    Route("/sessions/{session_id}", session_detail),
    Route("/memory", memory_page),
    Route("/skills", skills_list),
    Route("/skills/{name}", skill_detail_page),
    Mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static"),
]

exception_handlers = {
    404: not_found,
    500: server_error,
}

app = Starlette(
    routes=routes,
    exception_handlers=exception_handlers,
)
