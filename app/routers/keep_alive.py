'''
This module defines a simple keep-alive endpoint for the FastAPI application.
This endpoint can be used to check if the server is running and responsive.
Currently, it is being used to keep render from spinning down the server.
'''

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

@router.get("/ping", response_class=PlainTextResponse)
async def ping():
    return "A"
