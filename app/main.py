import socket
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from starlette.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from routers import router as api_router
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/templates", StaticFiles(directory="app/templates"), name="templates")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "default_dev_key"),
    max_age=60 * 60 * 24 * 15
)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
