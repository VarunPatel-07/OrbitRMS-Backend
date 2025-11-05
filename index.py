import asyncio
import json
import os

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from BackgroundDataHandler.DataSeederHelper import initializing_OrbitAdmin_On_App_start
from Config.EnvConfig import EnvConfig
from Database.CacheDatabase import cache_database
from Database.Database import DATABASE_ENGINE, SessionLocal, database
from Helper.helper import get_client_ip
from RateLimiting import custom_rate_limit_handler, limiter
from routes.Admin.Auth.authentication import adminAuthRoute
from routes.Admin.MaintenanceModeManager.MaintenanceModeManager import MaintenanceMode
from routes.Admin.Organization.EmployeeManager.EmployeeManager import adminOrgEmpControl
from routes.Admin.Organization.organization import adminOrgRoute
from routes.ApiManager.ApiManager import ApiManager
from routes.OrbitAi.OrbitAi import OrbitAiRoute

# from routes.Organizations.organizations import organization_router
from routes.auth.authentication import authRoutes
from routes.ClientInquires.ClientInquires import clientInquires
from routes.ConfigModule.ConfigModule import configRoute
from routes.CountryInfo.CountryInfo import countryApiRouter
from routes.ImageUploadation.ImageUploadation import imgRoute
from routes.Organizations.EmployeeController import employee_router
from routes.Organizations.FeedController import feedControl
from routes.Organizations.organizations import orgRouter
from routes.OrganizationSettings.OrganizationSettings import orgSettings
from routes.SocialMediaModule.Auth.SocialMedialAccountAuth import SocialAccountAuth
from routes.SocialMediaModule.SocialAccounts import SocialAccount
from Schedulers.BulkCommentFeeder import BulkCommentFeeder
from Schedulers.BulkLikeFeeder import BulkLikeFeeder
from Schedulers.MaintenanceModeScheduler import ping_maintenance_mode_scheduler
from SqlModels.Models import BaseModel

load_dotenv(override=True)

BACKEND_APP_ENVIRONMENT = os.getenv("BACKEND_APP_ENVIRONMENT")

app = FastAPI(
    title="OrbitRMS",
    description="Detailed API description.",
    version="1.0.0",
    contact={
        "name": "Varun Patel",
        "email": "varunspatelo7@gmail.com",
    },
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins. You can specify specific origins instead of "*".
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, etc.)
    allow_headers=["*"],  # Allows all headers
)


# Create database tables (consider using migrations instead)
BaseModel.metadata.create_all(bind=DATABASE_ENGINE)


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

scheduler = BackgroundScheduler()


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
async def root_health_check(request: Request):
    await cache_database.set("hello", "Valkey from FastAPI!", ex=10 * 24 * 3600)
    db_status = "healthy"

    # Check database connection
    try:
        await database.connect()
        await database.disconnect()
    except Exception:
        db_status = "unhealthy"

    if request.method == "GET":

        ip = get_client_ip(request)

        return {
            "message": "Welcome To OrbitRMS. The app functionality is working fine.",
            "database_status": db_status,
            "status": (
                "The app is healthy." if db_status == "healthy" else "Database connection issue."
            ),
            "cache_database": await cache_database.get("hello"),
            "ip": ip,
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


@app.api_route("/health", methods=["GET", "HEAD"], status_code=status.HTTP_200_OK)
async def health_status(request: Request):
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
                "The app is healthy." if db_status == "healthy" else "Database connection issue."
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
