from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


class DataModel(Base):
    __tablename__ = "datamodels"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    license: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    latest_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latest_digest: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    versions: Mapped[list["ModelVersion"]] = relationship(
        back_populates="datamodel", cascade="all, delete-orphan", passive_deletes=True
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("datamodel_id", "tag", name="uq_model_version_tag"),
        Index("ix_model_versions_datamodel_release", "datamodel_id", "release_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    datamodel_id: Mapped[int] = mapped_column(ForeignKey("datamodels.id", ondelete="CASCADE"), index=True)
    tag: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    digest: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    media_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    annotations: Mapped[dict] = mapped_column(JSON, default=dict)
    adms: Mapped[dict | list | str | None] = mapped_column(JSON, nullable=True)

    datamodel: Mapped[DataModel] = relationship(back_populates="versions")
    layers: Mapped[list["ModelLayer"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", passive_deletes=True
    )


class ModelLayer(Base):
    __tablename__ = "model_layers"
    __table_args__ = (UniqueConstraint("version_id", "digest", name="uq_model_layer_digest"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id", ondelete="CASCADE"), index=True)
    digest: Mapped[str] = mapped_column(String(255), index=True)
    media_type: Mapped[str] = mapped_column(String(255), index=True)
    size: Mapped[int | None] = mapped_column(nullable=True)
    annotations: Mapped[dict] = mapped_column(JSON, default=dict)

    version: Mapped[ModelVersion] = relationship(back_populates="layers")


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(64), default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_repositories: Mapped[int] = mapped_column(default=0)
    synced_repositories: Mapped[int] = mapped_column(default=0)
    failed_repositories: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    repositories: Mapped[list["SyncRepositoryState"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )


class SyncRepositoryState(Base):
    __tablename__ = "sync_repository_states"
    __table_args__ = (
        UniqueConstraint("run_id", "repository", name="uq_sync_run_repository"),
        Index("ix_sync_repository_states_run_status", "run_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("sync_runs.id", ondelete="CASCADE"), index=True)
    repository: Mapped[str] = mapped_column(String(512), index=True)
    status: Mapped[str] = mapped_column(String(64), default="pending", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[SyncRun] = relationship(back_populates="repositories")
