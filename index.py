from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth.authentication import routes
from SqlModels.Models import BaseModel
from Database.Database import DATABASE_ENGINE

app = FastAPI(
    title="Your API Title",
    description="Detailed API description.",
    version="1.0.0",
    contact={
        "name": "Your Name",
        "email": "your.email@example.com",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables (consider using migrations instead)
BaseModel.metadata.create_all(bind=DATABASE_ENGINE)

# Include application routes
app.include_router(routes)

