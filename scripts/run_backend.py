from __future__ import annotations

import uvicorn

from inference.config import BACKEND_HOST, BACKEND_PORT


if __name__ == "__main__":
    uvicorn.run("serving.main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=False)
