import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.datamodel import DataModel, ModelLayer, ModelVersion
from app.services.sync import SyncService


class FakeClient:
    async def tags(self, repository):
        return ["1.0.0"]

    async def manifest(self, repository, tag):
        return (
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "annotations": {
                    "org.opencontainers.image.title": "Duplicate Layer Model",
                    "org.opencontainers.image.created": "2026-01-01T00:00:00Z",
                },
                "layers": [
                    {"mediaType": "text/turtle", "digest": "sha256:duplicate", "size": 10},
                    {"mediaType": "text/turtle", "digest": "sha256:duplicate", "size": 10},
                ],
            },
            "sha256:manifest",
        )

    async def blob_json(self, repository, digest):
        return None


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.anyio
async def test_sync_repository_deduplicates_repeated_layer_digests(db_session):
    service = SyncService.__new__(SyncService)
    service.client = FakeClient()

    await service._sync_repository(db_session, "semantic/duplicate-layer-model")
    db_session.commit()

    datamodel = db_session.scalar(select(DataModel).where(DataModel.repository == "semantic/duplicate-layer-model"))
    version = db_session.scalar(select(ModelVersion).where(ModelVersion.datamodel_id == datamodel.id))
    layers = db_session.scalars(select(ModelLayer).where(ModelLayer.version_id == version.id)).all()

    assert len(layers) == 1
    assert layers[0].digest == "sha256:duplicate"


@pytest.mark.anyio
async def test_sync_repository_can_replace_existing_layers_with_same_digest(db_session):
    service = SyncService.__new__(SyncService)
    service.client = FakeClient()

    await service._sync_repository(db_session, "semantic/duplicate-layer-model")
    db_session.commit()
    await service._sync_repository(db_session, "semantic/duplicate-layer-model")
    db_session.commit()

    version = db_session.scalar(select(ModelVersion))
    layers = db_session.scalars(select(ModelLayer).where(ModelLayer.version_id == version.id)).all()

    assert len(layers) == 1
