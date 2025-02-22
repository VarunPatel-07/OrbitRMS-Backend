import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from Database.Database import DATABASE_ENGINE, database

# from routes.Organizations.organizations import organization_router
from routes.auth.authentication import authRoutes
from routes.CountryInfo.CountryInfo import countryApiRouter
from routes.Organizations.organizations import orgRouter
from SqlModels.Models import BaseModel


async def keep_alive():
    print("Running The Keep Alive function")
    print(f"vercel Env == {os.environ.get("VERCEL_ENV")}")
    if os.environ.get("VERCEL_ENV"):
        print("Keep-alive task started on Vercel environment")  # Print only once at start
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    development_url = "beta-stagging-orbit.vercel.app"
                    await client.get(f"https://{development_url}/", timeout=10.0)
                    await asyncio.sleep(180)  # 3 minutes
                except Exception as e:
                    print(f"Keep-alive ping failed: {str(e)}")  # Print only on error
                    await asyncio.sleep(30)
                    continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Running The Keep Alive function")
    print(f"vercel Env == {os.environ.get("VERCEL_ENV")}")
    if os.environ.get("VERCEL_ENV"):
        keep_alive_task = asyncio.create_task(keep_alive())
        yield
        keep_alive_task.cancel()
    else:
        yield


app = FastAPI(
    title="Your API Title",
    description="Detailed API description.",
    version="1.0.0",
    contact={
        "name": "Your Name",
        "email": "your.email@example.com",
    },
    lifespan=lifespan,
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


# Basic health check route
@app.get(path="/", status_code=status.HTTP_200_OK)
async def root_health_check():
    db_status = "healthy"

    # Check database connection
    try:
        await database.connect()
        await database.disconnect()
    except Exception:
        db_status = "unhealthy"

    return {
        "message": "Welcome To OrbitRMS. The app functionality is working fine.",
        "database_status": db_status,
        "status": (
            "The app is healthy." if db_status == "healthy" else "Database connection issue."
        ),
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_status():
    db_status = "healthy"

    # Check database connection
    try:
        await database.connect()
        await database.disconnect()
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "ok" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "message": (
            "The app is healthy." if db_status == "healthy" else "Database connection issue."
        ),
    }
