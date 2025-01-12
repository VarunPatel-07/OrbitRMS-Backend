from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth.authentication import routes
from  Database.Database import DATABASE_ENGINE , SessionLocal
import SqlModels.Models as Models


app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins. You can specify specific origins instead of "*".
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, etc.)
    allow_headers=["*"],  # Allows all headers
)


Models.BaseModel.metadata.create_all(bind=DATABASE_ENGINE)


app.include_router(routes)