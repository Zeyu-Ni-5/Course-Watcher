# app/models.py

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Watch(Base):
    __tablename__ = "watches"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    subject: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    catalog: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    component: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    term_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    snapshots: Mapped[list["Snapshot"]] = relationship(
        back_populates="watch",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "uq_watch_with_component",
            "subject",
            "catalog",
            "component",
            "term_code",
            unique=True,
            sqlite_where=text(
                "component IS NOT NULL"
            ),
        ),
        Index(
            "uq_watch_without_component",
            "subject",
            "catalog",
            "term_code",
            unique=True,
            sqlite_where=text(
                "component IS NULL"
            ),
        ),
    )


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    watch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "watches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    section: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    enrolled_total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    watch: Mapped[Watch] = relationship(
        back_populates="snapshots",
    )