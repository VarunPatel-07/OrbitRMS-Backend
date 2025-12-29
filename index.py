import asyncio
import os

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from config.EnvConfig import EnvConfig
from constants.constant import SERVER_ERROR_STATUS_CODE
from database.CacheDatabase import cache_database
from database.Database import DATABASE_ENGINE, SessionLocal, database
from jobs.backgroundHandler.DataSeederHelper import initializing_OrbitAdmin_On_App_start
from jobs.schedulers.BulkCommentFeeder import BulkCommentFeeder
from jobs.schedulers.BulkLikeFeeder import BulkLikeFeeder
from jobs.schedulers.MaintenanceModeScheduler import ping_maintenance_mode_scheduler
from middleware.CustomCorsMiddleWare import CustomCorsModule
from models.sql.Models import BaseModel
from middleware.RateLimiting import custom_rate_limit_handler, limiter
from routes.admin.auth.authentication import adminAuthRoute
from routes.admin.imageUploadation.ImageUploadation import adminImgRoute
from routes.admin.logsManager.logsController import logsController
from routes.admin.maintenance.MaintenanceModeManager import MaintenanceMode
from routes.admin.organization.AdminFeedController import adminFeedControl
from routes.admin.organization.EmployeeManager.EmployeeManager import adminOrgEmpControl
from routes.admin.organization.organization import adminOrgRoute
from routes.apiManager.ApiManager import ApiManager

# from routes.Organizations.organizations import organization_router
from routes.auth.authentication import authRoutes
from routes.clientInquires.ClientInquires import clientInquires
from routes.clientInquires.SubmitClientInquiry import publicInquiryRouter
from routes.configModule.ConfigModule import configRoute
from routes.countryInfo.CountryInfo import countryApiRouter
from routes.orbitAi.OrbitAi import OrbitAiRoute
from routes.organizations.Attendance import attendanceRoute
from routes.organizations.EmployeeController import employee_router
from routes.organizations.FeedController import feedControl
from routes.organizations.organizations import orgRouter
from routes.orgSettings.OrganizationSettings import orgSettings
from routes.socialMedia.Auth.SocialMedialAccountAuth import SocialAccountAuth
from routes.socialMedia.SocialAccounts import SocialAccount
from routes.uploadation.upload import imgRoute
from utils.logging.failureLogger import failureLogger
from utils.logging.runtimeLogger import runtimeLogger

load_dotenv(override=True)

BACKEND_APP_ENVIRONMENT = EnvConfig.BACKEND_APP_ENVIRONMENT
API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING

app = FastAPI(
    title="OrbitRMS",
    description="Detailed API description.",
    version="1.0.0",
    contact={
        "name": "Varun Patel",
        "email": "varunspatelo7@gmail.com",
    },
    redoc_url=None,
    docs_url=None if BACKEND_APP_ENVIRONMENT == "PRODUCTION" else "/docs",
    openapi_url=None if BACKEND_APP_ENVIRONMENT == "PRODUCTION" else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


app.add_middleware(CustomCorsModule)


# Create database tables (consider using migrations instead)
BaseModel.metadata.create_all(bind=DATABASE_ENGINE)


app.include_router(publicInquiryRouter)
# Include application routes
app.include_router(authRoutes)
app.include_router(orgRouter)
app.include_router(countryApiRouter)
app.include_router(imgRoute)
app.include_router(configRoute)
app.include_router(employee_router)
app.include_router(clientInquires)
app.include_router(orgSettings)
app.include_router(feedControl)
app.include_router(ApiManager)
app.include_router(adminAuthRoute)
app.include_router(adminOrgRoute)
app.include_router(adminOrgEmpControl)
app.include_router(MaintenanceMode)
app.include_router(SocialAccount)
app.include_router(SocialAccountAuth)
app.include_router(OrbitAiRoute)
app.include_router(attendanceRoute)
app.include_router(adminFeedControl)
app.include_router(adminImgRoute)
app.include_router(logsController)

scheduler = BackgroundScheduler()


@app.exception_handler(HTTPException)
async def global_exception_handler(request: Request, exc: HTTPException):

    if exc.status_code in SERVER_ERROR_STATUS_CODE:
        failureLogger.exception(f"Unhandled error at {request.url.path}")
    else:
        runtimeLogger.exception(f"Unhandled error at {request.url.path}")

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.on_event("startup")
async def initializing_scheduler_event():
    scheduler.add_job(ping_maintenance_mode_scheduler, "interval", minutes=1)
    scheduler.start()
    print("[Scheduler Started] Maintenance Mode Check is active.")


@app.on_event("startup")
async def initializing_OrbitAdmin():
    db: Session = SessionLocal()
    initializing_OrbitAdmin_On_App_start(db)


@app.on_event("startup")
async def startup_event():
    """
    On app startup, launch the background worker task
    """
    asyncio.create_task(worker_task())


async def worker_task():
    """
    Background task to process likes from Redis queue
    """
    db: Session = SessionLocal()

    asyncio.create_task(BulkLikeFeeder(db))
    asyncio.create_task(BulkCommentFeeder(db))


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("[Scheduler Stopped]")


# Basic health check route
@app.api_route(path="/", methods=["GET", "HEAD"], status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def root_health_check(request: Request):
    try:
        await cache_database.set("hello", "Valkey from FastAPI!", ex=10 * 24 * 3600)
        db_status = "healthy"

        # Check database connection
        try:
            await database.connect()
            await database.disconnect()
        except Exception:
            db_status = "unhealthy"

        if request.method == "GET":

            return {
                "message": "Welcome To OrbitRMS. The app functionality is working fine.",
                "database_status": db_status,
                "status": (
                    "The app is healthy."
                    if db_status == "healthy"
                    else "Database connection issue."
                ),
                "cache_database": await cache_database.get("hello"),
                "ENVIRONMENT": BACKEND_APP_ENVIRONMENT,
            }
        else:
            return Response(
                status_code=(
                    status.HTTP_200_OK
                    if db_status == "healthy"
                    else status.HTTP_503_SERVICE_UNAVAILABLE
                )
            )
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Verifying Admin",
                "error": str(e),
                "success": False,
            },
        )


@app.api_route("/health", methods=["GET", "HEAD"], status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def health_status(request: Request):
    try:
        db_status = "healthy"

        # Check database connection
        try:
            await database.connect()
            await database.disconnect()
        except Exception:
            db_status = "unhealthy"

        if request.method == "GET":
            return {
                "status": "ok" if db_status == "healthy" else "unhealthy",
                "database": db_status,
                "message": (
                    "The app is healthy."
                    if db_status == "healthy"
                    else "Database connection issue."
                ),
            }
        else:
            return Response(
                status_code=(
                    status.HTTP_200_OK
                    if db_status == "healthy"
                    else status.HTTP_503_SERVICE_UNAVAILABLE
                )
            )
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An Error Accrued While Health Check",
                "success": False,
                "error": str(e),
            },
        )
