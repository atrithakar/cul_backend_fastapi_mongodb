from fastapi import APIRouter
from .serve_files_cli import router as serve_files_cli
from .cli_funcs import router as cli_funcs
from .webui_routes import router as webui_routes

router = APIRouter()
router.include_router(serve_files_cli)
router.include_router(cli_funcs)
router.include_router(webui_routes)