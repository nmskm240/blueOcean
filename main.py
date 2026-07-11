from fastapi import FastAPI
import uvicorn

from blueOcean.routes.api import router as api_router
from blueOcean.routes.pages import router as pages_router
from blueOcean.strategy.routes_api import router as strategy_api_router
from blueOcean.strategy.routes_pages import router as strategy_pages_router
from blueOcean.app import lifespan, register_exception_handlers

app = FastAPI(title="BlueOcean Account Manager", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(pages_router)
app.include_router(api_router)
app.include_router(strategy_pages_router)
app.include_router(strategy_api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
