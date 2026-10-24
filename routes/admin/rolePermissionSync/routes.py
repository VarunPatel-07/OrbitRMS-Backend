from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from constants.constant import SUCCESS
from middleware.RateLimiting import limiter
from config.EnvConfig import EnvConfig
from database.Database import db_dependencies
from middleware.verifyToken import verify_token
from utils.responseMessages import ERROR_MESSAGE
from routes.admin.rolePermissionSync import service as serviceController

rolesPermissionSyncRoute = APIRouter(prefix="/app/v1/admin/role-permission", tags=["role-permission-sync"])


@rolesPermissionSyncRoute.post("/sync", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def rolesPermissionSync(
    request: Request,
    db: db_dependencies,
    dry_run: bool = Query(True, description="Only Report Changes Without Saving"),
    token: str = Depends(verify_token),
):
    try:
        return await serviceController.syncRolesAndPermissionServiceWorker(db, dry_run, token)
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ATTENDANCE_MODULE.ERROR_WHILE_APPLYING_LEAVE,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )
