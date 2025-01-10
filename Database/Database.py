import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from databases import Database
from fastapi.params import Depends
from typing import Annotated
from sqlalchemy.orm import Session

from dotenv import load_dotenv
load_dotenv()



DATABASE_URL = os.getenv('DATABASE_CONNECTION_STRING')
DATABASE_ENGINE = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=DATABASE_ENGINE , autoflush=False , autocommit=False)
BaseModel = declarative_base()

# Async database connection for databases library
database = Database(DATABASE_URL)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependencies = Annotated[Session , Depends(get_db)]