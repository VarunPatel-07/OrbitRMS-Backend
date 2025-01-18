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


app = FastAPI()



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
app.include_router(routes)

