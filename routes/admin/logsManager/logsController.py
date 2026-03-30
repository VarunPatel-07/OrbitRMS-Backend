import datetime
import io
import math
import os
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import joinedload

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from middleware.RateLimiting import limiter
from middleware.verifyToken import verify_token
from models.sql import Models
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

logsController = APIRouter(prefix="/app/v1/admin/monitoring")


API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING

BASE_DIR = Path(__file__).resolve().parents[3]
LOG_FILE_PATH = BASE_DIR / "logs" / "runtime" / "runtime.log"
FAILURE_LOG_FILE_PATH = BASE_DIR / "logs" / "failures" / "failures.log"

CURRENT_LOG_FOLDER_PATH = BASE_DIR / "logs" / "runtime"
ERROR_LOG_FOLDER_PATH = BASE_DIR / "logs" / "failures"

BASE_DOWNLOADABLE_FOLDER_PATH = BASE_DIR / "logs"


BACKUP_LOGS_BASE_DIR = BASE_DIR / "logs" / "archive"

BACKUP_CURRENT_LOG_FOLDER_PATH = BACKUP_LOGS_BASE_DIR / "runtime"
BACKUP_ERROR_LOG_FOLDER_PATH = BACKUP_LOGS_BASE_DIR / "failures"


def listAllFilesFromFolder(folder_path: Path, folder_name: str):
    if not folder_path.exists() and folder_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"The Provided Path Is Not A Valid Directory: {folder_path}",
                "success": SUCCESS.FALSE,
            },
        )
    files_details = []
    for file in folder_path.iterdir():
        stats = file.stat()
        size_in_byte = stats.st_size

        creation_time_timestamp = stats.st_ctime

        creation_time = datetime.datetime.fromtimestamp(creation_time_timestamp)

        data = {
            "file_name": file.name,
            "size": size_in_byte,
            "creation_time": creation_time,
            "file_path": f"{folder_name}/{file.name}",
        }
        files_details.append(data)

    return files_details


@logsController.get("/logs/runtime", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchAllLogs(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    page: Optional[int] = Query(alias="page"),
    limit: Optional[int] = Query(alias="limit"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ERROR_MESSAGE.UNAUTHORIZED,
                    "success": SUCCESS.FALSE,
                },
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ERROR_MESSAGE.INVALID_SESSION,
                    "success": SUCCESS.FALSE,
                },
            )

        page = page or 1
        limit = limit or 100
        start = (page - 1) * limit
        end = start + limit

        with open(LOG_FILE_PATH, "r") as log_file:
            file_content = list(log_file)[::-1]

        filtered_data = file_content[start:end]

        total_data = len(file_content)

        return {
            "message": SUCCESS_MESSAGE.READ_FILES_SUCCESS_FULLY,
            "success": SUCCESS.TRUE,
            "data": filtered_data,
            "metadata": {
                "total_data": total_data,
                "total_pages": math.ceil(total_data / limit),
                "current_page": page,
                "record_per_page": limit,
            },
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_READING_FILE,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@logsController.get("/logs/failures", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchAllLogs(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
    page: Optional[int] = Query(alias="page"),
    limit: Optional[int] = Query(alias="limit"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ERROR_MESSAGE.UNAUTHORIZED,
                    "success": SUCCESS.FALSE,
                },
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ERROR_MESSAGE.INVALID_SESSION,
                    "success": SUCCESS.FALSE,
                },
            )

        page = page or 1
        limit = limit or 100
        start = (page - 1) * limit
        end = start + limit

        with open(FAILURE_LOG_FILE_PATH, "r") as log_file:
            file_content = list(log_file)[::-1]

        filtered_data = file_content[start:end]

        total_data = len(file_content)

        return {
            "message": SUCCESS_MESSAGE.READ_FILES_SUCCESS_FULLY,
            "success": SUCCESS.TRUE,
            "data": filtered_data,
            "metadata": {
                "total_data": total_data,
                "total_pages": math.ceil(total_data / limit),
                "current_page": page,
                "record_per_page": limit,
            },
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_READING_FILE,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@logsController.get("/logs/history/files", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchAllTheBackUpFiles(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        current_files = listAllFilesFromFolder(CURRENT_LOG_FOLDER_PATH, "runtime")

        error_files = listAllFilesFromFolder(ERROR_LOG_FOLDER_PATH, "failures")

        backup_file_details = current_files + error_files

        return {
            "message": SUCCESS_MESSAGE.LOGS_FOLDER_READ_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": backup_file_details,
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_READING_FOLDER,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@logsController.get("/logs/archive/files", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchArchivedLogsFile(
    request: Request, db: db_dependencies, token: str = Depends(verify_token)
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        current_files = listAllFilesFromFolder(BACKUP_CURRENT_LOG_FOLDER_PATH, "archive/runtime")

        error_files = listAllFilesFromFolder(BACKUP_ERROR_LOG_FOLDER_PATH, "archive/failures")

        backup_file_details = current_files + error_files

        return {
            "message": SUCCESS_MESSAGE.BACKUP_FOLDER_READ_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": backup_file_details,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_READING_BACKUP_FOLDER,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


def iterfile(FILE_PATH: str):
    """Helper function to read a file in chunks."""
    with open(FILE_PATH, mode="rb") as f:
        yield from f


@logsController.get(
    "/logs/download-file/{file_path:path}",
)
@limiter.limit(API_RATE_LIMITING)
async def DownloadBackupFile(
    request: Request,
    db: db_dependencies,
    file_path: str,
    token: str = Depends(verify_token),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        full_path = (BASE_DOWNLOADABLE_FOLDER_PATH / file_path).resolve()

        if not str(full_path).startswith(str(BASE_DIR)):
            raise HTTPException(status_code=403, detail=ERROR_MESSAGE.ACCESS_DENIED)

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail=ERROR_MESSAGE.FILE_NOT_FOUND)

        headers = {"Content-Disposition": f'attachment; filename="{full_path.name}"'}

        return StreamingResponse(
            iterfile(str(full_path)), headers=headers, media_type="application/x-tar"
        )

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_DOWNLOADING_FROM_BACKUP_FOLDER,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )


@logsController.get(
    "/logs/archive/files/download-all",
)
@limiter.limit(API_RATE_LIMITING)
async def BulkDownloadArchiveFiles(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )
        current_files = listAllFilesFromFolder(BACKUP_CURRENT_LOG_FOLDER_PATH, "runtime")

        error_files = listAllFilesFromFolder(BACKUP_ERROR_LOG_FOLDER_PATH, "failures")

        archive_files = current_files + error_files

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file in archive_files:
                full_path = (BACKUP_LOGS_BASE_DIR / file.get("file_path")).resolve()

                if not str(full_path).startswith(str(BACKUP_LOGS_BASE_DIR)):
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": ERROR_MESSAGE.ACCESS_DENIED,
                            "success": SUCCESS.FALSE,
                            "data": None,
                        },
                    )

                if not full_path.exists() or not full_path.is_file():
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": ERROR_MESSAGE.FILE_NOT_FOUND,
                            "success": SUCCESS.FALSE,
                            "data": None,
                        },
                    )

                zip_file.write(full_path, arcname="archive-logs-files")

        zip_buffer.seek(0)

        headers = {"Content-Disposition": 'attachment; filename="logs_backup.zip"'}

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers=headers,
        )

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_IN_BULK_DOWNLOAD,
                "success": SUCCESS.FALSE,
                "error": str(e),
            },
        )
