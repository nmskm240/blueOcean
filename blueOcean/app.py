from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from peewee import SqliteDatabase

from blueOcean.container import get_injector
from blueOcean.database.schemas import AccountSchema, proxy
from blueOcean.metatrader.workers import MT5WorkerManager
from blueOcean.logging import get_logger


logger = get_logger(__name__)
templates = Jinja2Templates(directory=Path(__file__).parents[1] / "templates")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        client = request.client.host if request.client else "unknown"
        logger.exception(
            "Unexpected request error | method=%s path=%s client=%s",
            request.method,
            request.url.path,
            client,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        if request.url.path.startswith(("/api/", "/dialogs/")):
            return JSONResponse(
                status_code=500,
                content={"detail": "予想外のエラーが発生しました"},
            )
        return templates.TemplateResponse(
            request=request,
            name="error_500.html",
            context={},
            status_code=500,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    database = get_injector().get(SqliteDatabase)
    database_path = getattr(database, "database", None)
    if database_path and database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    proxy.initialize(database)
    with database.connection_context():
        database.create_tables([AccountSchema], safe=True)
        try:
            yield
        finally:
            get_injector().get(MT5WorkerManager).stop_all()
