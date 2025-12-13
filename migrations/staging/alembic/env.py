import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

load_dotenv()
# Add project root to Python path
project_root = Path(__file__).resolve().parents[3]  # Adjust based on your structure
sys.path.insert(0, str(project_root))

# Import your models (adjust import path as needed)
from SqlModels.Models import BaseModel

# Get current environment from folder structure
current_env = Path(__file__).resolve().parent.parent.name

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = BaseModel.metadata


def get_database_url():
    """Get URL based on current environment folder"""
    return os.getenv("STAGING_MIGRATION_DB_URL")


def run_migrations_online():
    connectable = create_engine(
        get_database_url(),
        poolclass=pool.NullPool,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"ssl": {"ca": "/path/to/ca-cert.pem"} if current_env == "staging" else {}},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=f"alembic_version_{current_env}",
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
