from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.cases import get_case_repository
from app.database_safety import DatabaseInspection, DatabaseSafetyService
from app.persistence.sqlite_case_repository import SQLiteCaseRepository

router = APIRouter(prefix="/api/database", tags=["database"])
MAX_IMPORT_BYTES = 100 * 1024 * 1024


class BackupRequest(BaseModel):
    label: str = Field(default="manual", min_length=1, max_length=60)


class RestoreRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    performed_by: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=500)
    confirm_restore: bool


class InspectionResponse(BaseModel):
    filename: str
    integrity: str
    valid: bool
    schema_version: int | None
    case_count: int
    size_bytes: int
    sha256: str
    created_at: str


class BackupListResponse(BaseModel):
    backups: list[InspectionResponse]
    count: int


def get_database_safety_service(
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> DatabaseSafetyService:
    return DatabaseSafetyService(repository.database_path)


def _inspection_response(inspection: DatabaseInspection) -> InspectionResponse:
    return InspectionResponse(**asdict(inspection))


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/integrity", response_model=InspectionResponse)
def inspect_database(
    service: DatabaseSafetyService = Depends(get_database_safety_service),
) -> InspectionResponse:
    try:
        return _inspection_response(service.inspect_live())
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_error(exc) from exc


@router.get("/backups", response_model=BackupListResponse)
def list_backups(
    service: DatabaseSafetyService = Depends(get_database_safety_service),
) -> BackupListResponse:
    backups = [_inspection_response(inspection) for inspection in service.list_backups()]
    return BackupListResponse(backups=backups, count=len(backups))


@router.post("/backups", response_model=InspectionResponse, status_code=201)
def create_backup(
    request: BackupRequest,
    service: DatabaseSafetyService = Depends(get_database_safety_service),
) -> InspectionResponse:
    try:
        return _inspection_response(service.create_backup(label=request.label))
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_error(exc) from exc


@router.post("/backups/import", response_model=InspectionResponse, status_code=201)
async def import_backup(
    request: Request,
    filename: str = Query(min_length=1, max_length=255),
    service: DatabaseSafetyService = Depends(get_database_safety_service),
) -> InspectionResponse:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Backup import exceeds the 100 MB limit.")
    content = await request.body()
    if not content:
        raise HTTPException(status_code=422, detail="Backup import is empty.")
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Backup import exceeds the 100 MB limit.")
    try:
        return _inspection_response(service.import_backup(content, original_filename=filename))
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_error(exc) from exc


@router.get("/backups/{filename}/download")
def download_backup(
    filename: str,
    service: DatabaseSafetyService = Depends(get_database_safety_service),
) -> FileResponse:
    try:
        inspection = service.inspect_backup(filename)
        if not inspection.valid:
            raise ValueError(f"Backup integrity check failed: {inspection.integrity}")
        path = service.backup_path(filename)
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_error(exc) from exc
    return FileResponse(path, media_type="application/vnd.sqlite3", filename=filename)


@router.get("/backups/{filename}/preview", response_model=InspectionResponse)
def preview_backup(
    filename: str,
    service: DatabaseSafetyService = Depends(get_database_safety_service),
) -> InspectionResponse:
    try:
        return _inspection_response(service.inspect_backup(filename))
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_error(exc) from exc


@router.post("/restore")
def restore_backup(
    request: RestoreRequest,
    service: DatabaseSafetyService = Depends(get_database_safety_service),
) -> dict[str, object]:
    if not request.confirm_restore:
        raise HTTPException(status_code=422, detail="Restore requires explicit confirmation.")
    try:
        result = service.restore_backup(
            request.filename,
            performed_by=request.performed_by,
            reason=request.reason,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_error(exc) from exc
    return {
        "restored": asdict(result["restored"]),
        "pre_restore_backup": asdict(result["pre_restore_backup"]),
        "audit": result["audit"],
    }
