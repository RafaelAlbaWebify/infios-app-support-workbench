from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["ui"])
UI_DIR = Path(__file__).resolve().parents[1] / "ui"


@router.get("/", include_in_schema=False)
def guided_workbench() -> FileResponse:
    return FileResponse(UI_DIR / "index.html", media_type="text/html")


@router.get("/analytics", include_in_schema=False)
def operational_analytics() -> FileResponse:
    return FileResponse(UI_DIR / "analytics.html", media_type="text/html")


@router.get("/problems", include_in_schema=False)
def problem_management() -> FileResponse:
    return FileResponse(UI_DIR / "problems.html", media_type="text/html")
