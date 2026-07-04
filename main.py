from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


app = FastAPI(title="Orbit Dashboard")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")


@app.get("/partials/empty-state", response_class=HTMLResponse)
async def empty_state(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="partials/empty_state.html",
        context={"refreshed_at": datetime.now(timezone.utc).strftime("%H:%M UTC")},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
