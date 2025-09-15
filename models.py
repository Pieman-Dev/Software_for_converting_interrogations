"""SQLAlchemy‑модели, соответствующие структуре БД.
Импортируются во всём проекте как:
    import models
и дают доступ к Base.metadata для Alembic autogenerate.
"""
from __future__ import annotations

import enum
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Enum as SqlEnum
from sqlalchemy.sql import func

from db import Base

# ───────────────────── Вспомогательные enum‑ы ─────────────────────
class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done    = "done"
    error   = "error"

# ───────────────────────── Таблицы ────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True)
    email         = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:  # noqa: D401
        return f"<User {self.id} {self.email}>"


class AudioFile(Base):
    __tablename__ = "audio_files"

    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    original_path = Column(String, nullable=False)
    duration      = Column(Integer)  # секунды
    uploaded_at   = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:  # noqa: D401
        return f"<AudioFile {self.id} path={self.original_path}>"


class Transcript(Base):
    __tablename__ = "transcripts"

    id         = Column(Integer, primary_key=True)
    audio_id   = Column(Integer, ForeignKey("audio_files.id", ondelete="CASCADE"), nullable=False)
    language   = Column(String(8))
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:  # noqa: D401
        return f"<Transcript {self.id} audio={self.audio_id}>"


class Job(Base):
    __tablename__ = "jobs"

    id          = Column(Integer, primary_key=True)
    audio_id    = Column(Integer, ForeignKey("audio_files.id", ondelete="CASCADE"), nullable=False)
    model_name  = Column(String, nullable=False)
    status      = Column(SqlEnum(JobStatus), nullable=False, default=JobStatus.pending)
    started_at  = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    error_msg   = Column(Text)

    def __repr__(self) -> str:  # noqa: D401
        return f"<Job {self.id} {self.status}>"