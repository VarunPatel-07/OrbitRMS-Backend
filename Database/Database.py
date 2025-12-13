import logging
from typing import Annotated

from databases import Database
from dotenv import load_dotenv
from fastapi.params import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from Config.EnvConfig import EnvConfig

load_dotenv(override=True)


DATABASE_ENGINE = create_engine(
    EnvConfig.DATABASE_CONNECTION_STRING,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=280,
    connect_args={
        "connect_timeout": 10,
        "read_timeout": 10,
        "write_timeout": 10,
    },
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
