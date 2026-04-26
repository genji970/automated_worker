from __future__ import annotations

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from serving.api.routes import router


app = FastAPI(title="Serving Backend", version="0.4.0")
app.include_router(router)

Instrumentator().instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")
