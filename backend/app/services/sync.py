from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.datamodel import DataModel, ModelLayer, ModelVersion
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
        sync_state.start()
        logger.info("Starting OCI registry sync")
        repositories = await self.client.catalog()
        allowed_repositories = [repo for repo in repositories if is_allowed(repo, self.settings.allowlist_patterns)]
        sync_state.phase = "syncing_repositories"
        sync_state.total_repositories = len(allowed_repositories)
        logger.info("Discovered %s repositories, %s allowed", len(repositories), len(allowed_repositories))
        seen = set(allowed_repositories)

        try:
            for index, repository in enumerate(allowed_repositories, start=1):
                sync_state.current_repository = repository
                logger.info("Syncing repository %s/%s: %s", index, len(allowed_repositories), repository)
                await self._sync_repository(db, repository)
                sync_state.synced_repositories = index

            sync_state.phase = "removing_deleted_repositories"
            existing = db.scalars(select(DataModel)).all()
            for datamodel in existing:
                if datamodel.repository not in seen:
                    db.delete(datamodel)
            db.commit()
            logger.info("Finished OCI registry sync")
            result = {"repositories": len(allowed_repositories), "synced_at": datetime.now(timezone.utc).isoformat()}
            sync_state.finish()
            return result
        except Exception as exc:
            db.rollback()
            sync_state.fail(exc)
            logger.exception("OCI registry sync failed")
            raise

    async def _sync_repository(self, db: Session, repository: str) -> None:
        tags = await self.client.tags(repository)
        version_payloads = []
        datamodel = db.scalar(select(DataModel).where(DataModel.repository == repository))
        if datamodel is None:
            datamodel = DataModel(repository=repository, title=repository)
            db.add(datamodel)
            db.flush()

        existing_versions = {version.tag: version for version in datamodel.versions}
        seen_tags = set(tags)
        for tag in tags:
            manifest, digest = await self.client.manifest(repository, tag)
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
