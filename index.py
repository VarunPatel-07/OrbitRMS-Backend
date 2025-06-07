from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from Database.CacheDatabase import cache_database
from Database.Database import DATABASE_ENGINE, database

# from routes.Organizations.organizations import organization_router
from routes.auth.authentication import authRoutes
from routes.ConfigModule.ConfigModule import configRoute
from routes.CountryInfo.CountryInfo import countryApiRouter
from routes.ImageUploadation.ImageUploadation import imgRoute
from routes.Organizations.EmployeeController import employee_router
from routes.Organizations.organizations import orgRouter
from SqlModels.Models import BaseModel
from Helper.helper import get_client_ip

from user_agents import parse as parse_user_agent

app = FastAPI(
    title="OrbitRMS",
    description="Detailed API description.",
    version="1.0.0",
    contact={
        "name": "Varun Patel",
        "email": "varunspatelo7@gmail.com",
    },
)


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
        user_agent_string = request.headers.get("user-agent", "unknown")
        user_agent = parse_user_agent(user_agent_string)

        device_fingerprint = f"{user_agent_string}-{ip}"

        device_info = {
            "ip_address": ip,
            "browser": user_agent.browser.family,
            "browser_version": user_agent.browser.version_string,
            "os": user_agent.os.family,
            "os_version": user_agent.os.version_string,
            "device_type": user_agent.device.family,
            "is_mobile": user_agent.is_mobile,
            "is_tablet": user_agent.is_tablet,
            "is_pc": user_agent.is_pc,
            "is_bot": user_agent.is_bot,
            "fingerprint": device_fingerprint,
        }

        return {
            "message": "Welcome To OrbitRMS. The app functionality is working fine.",
            "database_status": db_status,
            "status": (
                "The app is healthy." if db_status == "healthy" else "Database connection issue."
            ),
            "cache_database": await cache_database.get("hello"),
            "device_info": device_info,
            "device_fingerprint": device_fingerprint,
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
