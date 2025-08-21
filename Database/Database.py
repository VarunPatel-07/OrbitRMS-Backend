import logging
from Config.EnvConfig import EnvConfig
from typing import Annotated

from databases import Database
from dotenv import load_dotenv
from fastapi.params import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv(override=True)


DATABASE_ENGINE = create_engine(
    EnvConfig.DATABASE_CONNECTION_STRING,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=DATABASE_ENGINE, autoflush=False, autocommit=False)


# Async database connection for databases library
database = Database(EnvConfig.DATABASE_CONNECTION_STRING)


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logging.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


db_dependencies = Annotated[Session, Depends(get_db)]
