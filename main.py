from fastapi import FastAPI
import uvicorn

from blueOcean.routes.api import router as api_router
from blueOcean.routes.pages import router as pages_router
from blueOcean.app import lifespan

app = FastAPI(title="BlueOcean Account Manager", lifespan=lifespan)
app.include_router(pages_router)
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
