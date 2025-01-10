from fastapi import FastAPI
from routes.auth.authentication import routes
from  Database.Database import DATABASE_ENGINE , SessionLocal
import SqlModels.Models as Models

app = FastAPI()
Models.BaseModel.metadata.create_all(bind=DATABASE_ENGINE)


app.include_router(routes)