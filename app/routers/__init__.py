'''
This file is the entry point for all the routers in the app/routers directory. It imports all the routers and includes them in the main router object. This allows the main router object to include all the routes defined in the individual routers.
'''

from fastapi import APIRouter
from .serve_files_cli import router as serve_files_cli
from .cli_funcs import router as cli_funcs
from .webui_routes import router as webui_routes
from .keep_alive import router as keep_alive

router = APIRouter()
router.include_router(serve_files_cli)
router.include_router(cli_funcs)
router.include_router(webui_routes)
router.include_router(keep_alive)