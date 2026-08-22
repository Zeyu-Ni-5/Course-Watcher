# app/database.py

import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    sessionmaker,
)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./course_watcher.db",
)

engine_arguments = {}

if DATABASE_URL.startswith("sqlite"):
    engine_arguments["connect_args"] = {
        "check_same_thread": False,
    }

engine = create_engine(
    DATABASE_URL,
    **engine_arguments,
)


if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()