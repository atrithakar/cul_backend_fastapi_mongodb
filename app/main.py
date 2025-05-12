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
app.add_middleware(SessionMiddleware, secret_key="atri")

app.add_middleware(
    SessionMiddleware,
    secret_key = "atri",
    max_age = 60 * 60 * 24 * 15
)

def get_host_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    uvicorn.run(app, host=get_host_ip(), port=8000)