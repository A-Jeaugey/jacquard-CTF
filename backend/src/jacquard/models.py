"""Modèle de données.

Les défis et la configuration de l'événement sont importés depuis le pack ; ils sont
identifiés par leur `id` stable, ce qui permet de resynchroniser un pack sans perdre les
résolutions existantes.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jacquard.db import Base


class EventRow(Base):
    """Configuration de l'événement importée du pack (une seule ligne, id = 1)."""

    __tablename__ = "event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    slug: Mapped[str] = mapped_column(String(64))
    config: Mapped[dict[str, Any]] = mapped_column(JSON)
    pack_digest: Mapped[str] = mapped_column(String(64))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    name_key: Mapped[str] = mapped_column(String(64), unique=True)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["User"]] = relationship(back_populates="team")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32))
    username_key: Mapped[str] = mapped_column(String(32), unique=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="player")
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped[Team | None] = relationship(back_populates="members")

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class AuthSession(Base):
    """Session de connexion. Seul le condensat du jeton est stocké."""

    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginFailure(Base):
    __tablename__ = "login_failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username_key: Mapped[str] = mapped_column(String(32), index=True)
    ip: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    authors: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    description_html: Mapped[str] = mapped_column(Text, default="")
    scoring: Mapped[dict[str, Any]] = mapped_column(JSON)
    connection: Mapped[str | None] = mapped_column(String(512), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Un défi retiré du pack est désactivé, jamais supprimé, pour conserver les résolutions.
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    flags: Mapped[list["Flag"]] = relationship(
        back_populates="challenge", cascade="all, delete-orphan"
    )
    files: Mapped[list["ChallengeFile"]] = relationship(
        back_populates="challenge", cascade="all, delete-orphan"
    )


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))  # static | regex
    # `static` : HMAC du flag normalisé. `regex` : motif en clair.
    value: Mapped[str] = mapped_column(Text)
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=True)

    challenge: Mapped[Challenge] = relationship(back_populates="flags")


class ChallengeFile(Base):
    __tablename__ = "challenge_files"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    challenge_id: Mapped[str] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)

    challenge: Mapped[Challenge] = relationship(back_populates="files")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    challenge_id: Mapped[str] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), index=True
    )
    provided: Mapped[str] = mapped_column(String(512))
    correct: Mapped[bool] = mapped_column(Boolean)
    ip: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Solve(Base):
    __tablename__ = "solves"
    __table_args__ = (UniqueConstraint("team_id", "challenge_id", name="uq_solve_team_challenge"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    challenge_id: Mapped[str] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    body_html: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
