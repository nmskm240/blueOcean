from contextlib import asynccontextmanager

from fastapi import FastAPI

from blueOcean.api import router
from blueOcean.process_manager import CounterProcessManager
from blueOcean.settings import REDIS_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = CounterProcessManager(REDIS_URL)
    app.state.process_manager = manager
    try:
        yield
    finally:
        manager.shutdown()


def create_app() -> FastAPI:
    application = FastAPI(title="Orbit Dashboard", lifespan=lifespan)
    application.include_router(router)
    return application


app = create_app()
