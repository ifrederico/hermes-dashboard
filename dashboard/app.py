"""Hermes Dashboard — Starlette app with Jinja2 templates."""

from pathlib import Path

import markdown
import yaml
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from dashboard.readers import sessions, memory, skills, cron, hermes_config
from dashboard.config import config_yaml_path

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# --- Route handlers ---

async def index(request: Request):
    stats = sessions.get_stats()
    skill_list = skills.list_skills()
    recent, _ = sessions.list_sessions(limit=8, include_subagents=False)
    return templates.TemplateResponse(request, "index.html", {
        "page": "index",
        "stats": stats,
        "skill_count": len(skill_list),
        "recent_sessions": recent,
    })


async def sessions_list(request: Request):
    query = request.query_params.get("q", "").strip()
    show_sub = request.query_params.get("show_sub", "0") == "1"
    offset = int(request.query_params.get("offset", "0"))
    limit = 30

    if query:
        session_list = sessions.search_sessions(query, limit=limit)
        total = len(session_list)
    else:
        session_list, total = sessions.list_sessions(
            limit=limit, offset=offset, include_subagents=show_sub
        )

    return templates.TemplateResponse(request, "sessions.html", {
        "page": "sessions",
        "sessions": session_list,
        "total": total,
        "offset": offset,
        "limit": limit,
        "query": query,
        "show_subagents": show_sub,
    })


async def session_detail(request: Request):
    session_id = request.path_params["session_id"]
    session = sessions.get_session(session_id)
    if not session:
        return templates.TemplateResponse(request, "404.html", status_code=404)

    chain = sessions.get_conversation_chain(session_id)
    msgs = sessions.get_messages(session_id)

    return templates.TemplateResponse(request, "session_detail.html", {
        "page": "sessions",
        "session": session,
        "chain": chain,
        "messages": msgs,
        "show_system": request.query_params.get("system", "0") == "1",
    })


async def memory_page(request: Request):
    saved = request.query_params.get("saved", "")
    editing = request.query_params.get("edit", "")
    mem = memory.get_memory()
    user = memory.get_user_profile()
    return templates.TemplateResponse(request, "memory.html", {
        "page": "memory",
        "memory": mem,
        "user_profile": user,
        "editing": editing,
        "saved": saved,
    })


async def memory_save(request: Request):
    form = await request.form()
    target = form.get("target", "")
    content = form.get("content", "")
    if target == "memory":
        memory.save_memory(content)
    elif target == "user":
        memory.save_user_profile(content)
    return RedirectResponse(url="/memory?saved=" + target, status_code=303)


async def skills_list(request: Request):
    skill_list = skills.list_skills()
    return templates.TemplateResponse(request, "skills.html", {
        "page": "skills",
        "skills": skill_list,
    })


async def skill_detail(request: Request):
    name = request.path_params["name"]
    skill = skills.get_skill(name)
    if not skill:
        return templates.TemplateResponse(request, "404.html", status_code=404)

    body_html = markdown.markdown(
        skill.body,
        extensions=["fenced_code", "tables", "toc"],
    )

    return templates.TemplateResponse(request, "skill_detail.html", {
        "page": "skills",
        "skill": skill,
        "body_html": body_html,
    })


async def skill_delete(request: Request):
    name = request.path_params["name"]
    form = await request.form()
    if form.get("confirm") == "yes":
        skills.delete_skill(name)
    return RedirectResponse(url="/skills", status_code=303)


async def cron_list(request: Request):
    jobs = cron.list_jobs()
    return templates.TemplateResponse(request, "cron.html", {
        "page": "cron",
        "jobs": jobs,
    })


async def cron_detail(request: Request):
    job_id = request.path_params["job_id"]
    job = cron.get_job(job_id)
    if not job:
        return templates.TemplateResponse(request, "404.html", status_code=404)

    outputs = cron.get_job_outputs(job_id)

    return templates.TemplateResponse(request, "cron_detail.html", {
        "page": "cron",
        "job": job,
        "outputs": outputs,
    })


async def config_page(request: Request):
    config = hermes_config.read_config_redacted()
    config_str = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return templates.TemplateResponse(request, "config.html", {
        "page": "config",
        "config_yaml": config_str,
        "config_path": str(config_yaml_path()),
    })


async def not_found(request: Request, exc):
    return templates.TemplateResponse(request, "404.html", status_code=404)


# --- App ---

routes = [
    Route("/", index),
    Route("/sessions", sessions_list),
    Route("/sessions/{session_id:path}", session_detail),
    Route("/memory", memory_page),
    Route("/memory/save", memory_save, methods=["POST"]),
    Route("/skills", skills_list),
    Route("/skills/{name:str}", skill_detail),
    Route("/skills/{name:str}/delete", skill_delete, methods=["POST"]),
    Route("/cron", cron_list),
    Route("/cron/{job_id:str}", cron_detail),
    Route("/config", config_page),
    Mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static"),
]

app = Starlette(
    routes=routes,
    exception_handlers={404: not_found},
)
