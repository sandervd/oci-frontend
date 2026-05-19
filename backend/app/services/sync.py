from datetime import datetime, timezone
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models.datamodel import DataModel, ModelLayer, ModelVersion, SyncRepositoryState, SyncRun
from app.services.allowlist import is_allowed
from app.services.metadata import choose_latest, summarize
from app.services.oci_client import OCIClient
from app.services.sync_state import sync_state


logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OCIClient(settings.registry_base_url, settings.oci_username, settings.oci_password)

    async def sync(self, db: Session) -> dict:
        run = self._get_or_create_run(db)
        sync_state.start(run.id)
        logger.info("Starting OCI registry sync run %s", run.id)
        repositories = await self.client.catalog()
        allowed_repositories = [repo for repo in repositories if is_allowed(repo, self.settings.allowlist_patterns)]
        self._ensure_repository_states(db, run, allowed_repositories)
        sync_state.phase = "syncing_repositories"
        sync_state.total_repositories = len(allowed_repositories)
        sync_state.synced_repositories = run.synced_repositories
        sync_state.failed_repositories = run.failed_repositories
        logger.info("Discovered %s repositories, %s allowed", len(repositories), len(allowed_repositories))
        seen = set(allowed_repositories)

        try:
            states = self._repository_states_to_process(db, run.id)
            sync_state.skipped_repositories = len(allowed_repositories) - len(states)
            for index, state in enumerate(states, start=1):
                sync_state.current_repository = state.repository
                logger.info(
                    "Syncing repository %s/%s for run %s: %s",
                    run.synced_repositories + run.failed_repositories + index,
                    len(allowed_repositories),
                    run.id,
                    state.repository,
                )
                state.status = "syncing"
                state.started_at = datetime.now(timezone.utc)
                state.finished_at = None
                state.error = None
                db.commit()

                try:
                    await self._sync_repository(db, state.repository)
                    state.status = "completed"
                    state.finished_at = datetime.now(timezone.utc)
                    state.error = None
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    state = db.scalar(select(SyncRepositoryState).where(SyncRepositoryState.id == state.id))
                    if state is not None:
                        state.status = "failed"
                        state.finished_at = datetime.now(timezone.utc)
                        state.error = str(exc)
                    db.commit()
                    logger.exception("Failed to sync repository %s", sync_state.current_repository)

                self._refresh_run_counts(db, run)
                sync_state.synced_repositories = run.synced_repositories
                sync_state.failed_repositories = run.failed_repositories

            if run.failed_repositories == 0:
                sync_state.phase = "removing_deleted_repositories"
                existing = db.scalars(select(DataModel)).all()
                for datamodel in existing:
                    if datamodel.repository not in seen:
                        db.delete(datamodel)
                run.status = "completed"
            else:
                run.status = "completed_with_errors"
                run.error = f"{run.failed_repositories} repositories failed"
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("Finished OCI registry sync run %s with status %s", run.id, run.status)
            result = {
                "run_id": run.id,
                "status": run.status,
                "repositories": len(allowed_repositories),
                "synced_repositories": run.synced_repositories,
                "failed_repositories": run.failed_repositories,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
            sync_state.finish()
            return result
        except Exception as exc:
            db.rollback()
            run = db.scalar(select(SyncRun).where(SyncRun.id == run.id))
            if run is not None:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                run.error = str(exc)
                db.commit()
            sync_state.fail(exc)
            logger.exception("OCI registry sync failed")
            raise

    async def _sync_repository(self, db: Session, repository: str) -> None:
        tags = await self.client.tags(repository)
        version_payloads = []
        datamodel = db.scalar(
            select(DataModel)
            .where(DataModel.repository == repository)
            .options(selectinload(DataModel.versions).selectinload(ModelVersion.layers))
        )
        if datamodel is None:
            datamodel = DataModel(repository=repository, title=repository)
            db.add(datamodel)
            db.flush()

        existing_versions = {version.tag: version for version in datamodel.versions}
        seen_tags = set(tags)
        for tag in tags:
            manifest, digest = await self.client.manifest(repository, tag)
            existing = existing_versions.get(tag)
            if existing is not None and existing.digest == digest:
                version_payloads.append(
                    {
                        "tag": existing.tag,
                        "version": existing.version,
                        "title": existing.title,
                        "description": existing.description,
                        "license": existing.license,
                        "domains": existing.domains,
                        "release_date": existing.release_date,
                        "digest": existing.digest,
                    }
                )
                continue

            config_blob = None
            config = manifest.get("config") or {}
            if config.get("digest"):
                config_blob = await self.client.blob_json(repository, config["digest"])
            payload = summarize(repository, tag, manifest, config_blob)
            payload["digest"] = digest
            version_payloads.append(payload)

            version = existing_versions.get(tag) or ModelVersion(datamodel=datamodel, tag=tag)
            version.version = payload["version"]
            version.digest = digest
            version.title = payload["title"]
            version.description = payload["description"]
            version.license = payload["license"]
            version.domains = payload["domains"]
            version.release_date = payload["release_date"]
            version.media_type = payload["media_type"]
            version.annotations = payload["annotations"]
            version.adms = payload["adms"]
            db.add(version)
            db.flush()

            version.layers.clear()
            for layer in payload["layers"]:
                if not layer.get("digest"):
                    continue
                db.add(
                    ModelLayer(
                        version=version,
                        digest=layer["digest"],
                        media_type=layer.get("mediaType") or "application/octet-stream",
                        size=layer.get("size"),
                        annotations=layer.get("annotations") or {},
                    )
                )

        for tag, version in existing_versions.items():
            if tag not in seen_tags:
                db.delete(version)

        latest = choose_latest(version_payloads)
        if latest:
            datamodel.title = latest["title"]
            datamodel.description = latest["description"]
            datamodel.license = latest["license"]
            datamodel.domains = latest["domains"]
            datamodel.latest_tag = latest["tag"]
            datamodel.latest_digest = latest["digest"]
            datamodel.updated_at = latest["release_date"]
        db.flush()

    def _get_or_create_run(self, db: Session) -> SyncRun:
        run = db.scalar(
            select(SyncRun)
            .where(SyncRun.status.in_(["running", "failed", "completed_with_errors"]))
            .order_by(SyncRun.started_at.desc(), SyncRun.id.desc())
        )
        if run is None:
            run = SyncRun(status="running")
            db.add(run)
            db.commit()
            db.refresh(run)
            return run

        run.status = "running"
        run.finished_at = None
        run.error = None
        for state in run.repositories:
            if state.status == "syncing":
                state.status = "pending"
                state.finished_at = None
                state.error = "Reset after interrupted sync"
        db.commit()
        db.refresh(run)
        return run

    def _ensure_repository_states(self, db: Session, run: SyncRun, repositories: list[str]) -> None:
        existing = {
            state.repository
            for state in db.scalars(select(SyncRepositoryState).where(SyncRepositoryState.run_id == run.id)).all()
        }
        for repository in repositories:
            if repository not in existing:
                db.add(SyncRepositoryState(run_id=run.id, repository=repository, status="pending"))
        run.total_repositories = len(repositories)
        db.commit()
        self._refresh_run_counts(db, run)

    def _repository_states_to_process(self, db: Session, run_id: int) -> list[SyncRepositoryState]:
        return db.scalars(
            select(SyncRepositoryState)
            .where(SyncRepositoryState.run_id == run_id, SyncRepositoryState.status.in_(["pending", "failed"]))
            .order_by(SyncRepositoryState.repository)
        ).all()

    def _refresh_run_counts(self, db: Session, run: SyncRun) -> None:
        run.synced_repositories = db.scalar(
            select(func.count()).select_from(SyncRepositoryState).where(
                SyncRepositoryState.run_id == run.id,
                SyncRepositoryState.status == "completed",
            )
        ) or 0
        run.failed_repositories = db.scalar(
            select(func.count()).select_from(SyncRepositoryState).where(
                SyncRepositoryState.run_id == run.id,
                SyncRepositoryState.status == "failed",
            )
        ) or 0
        db.commit()
