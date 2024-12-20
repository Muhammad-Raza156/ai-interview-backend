import sys
from pathlib import Path
from dotenv import load_dotenv
import os

from app.db.session import engine
from app.db.base import Base
from app.models import user 
from sqlalchemy import engine_from_config, pool
from alembic import context

load_dotenv()

target_metadata = Base.metadata

config = context.config

config.set_section_option("alembic", "sqlalchemy.url")

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        echo=True
        )

    # Configure the context with the database connection
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()