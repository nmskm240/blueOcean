from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from blueOcean.process_manager import CounterProcessManager


router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def get_manager(request: Request) -> CounterProcessManager:
    return request.app.state.process_manager


def render_counters(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="partials/counters.html",
        context={"counters": get_manager(request).snapshot()},
    )


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")


@router.get("/partials/empty-state", response_class=HTMLResponse)
async def empty_state(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="partials/empty_state.html",
        context={"refreshed_at": datetime.now(timezone.utc).strftime("%H:%M UTC")},
    )


@router.get("/partials/counters", response_class=HTMLResponse)
async def counter_status(request: Request):
    return render_counters(request)


@router.post("/counters", response_class=HTMLResponse)
async def counter_create(request: Request):
    get_manager(request).create()
    return render_counters(request)


@router.post("/counters/{counter_id}/start", response_class=HTMLResponse)
async def counter_start(request: Request, counter_id: str):
    get_manager(request).start(counter_id)
    return render_counters(request)


@router.post("/counters/{counter_id}/stop", response_class=HTMLResponse)
async def counter_stop(request: Request, counter_id: str):
    get_manager(request).stop(counter_id)
    return render_counters(request)


@router.delete("/counters/{counter_id}", response_class=HTMLResponse)
async def counter_delete(request: Request, counter_id: str):
    get_manager(request).delete(counter_id)
    return render_counters(request)
