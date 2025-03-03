import os
import json
import io
import zipfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from starlette.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from routers import router as api_router
from fastapi.staticfiles import StaticFiles
from database import get_database
from models import Module, User

app = FastAPI()
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/templates", StaticFiles(directory="app/templates"), name="templates")
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

if __name__ == "__main__":
    uvicorn.run(app, host="192.168.0.104", port=8000)