from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
import httpx
from sqlalchemy.exc import OperationalError
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.datamodel import DataModel, ModelLayer, ModelVersion, SyncRepositoryState, SyncRun
from app.schemas.datamodel import DataModelDetail, FacetValue, SearchResponse
from app.services.oci_client import OCIClient
from app.services.sync import SyncService
from app.services.sync_lock import sync_lock
from app.services.sync_state import sync_state

router = APIRouter(prefix="/api")


@router.get("/datamodels", response_model=SearchResponse)
def search_datamodels(
    q: str | None = None,
    license: list[str] = Query(default=[]),
    domain: list[str] = Query(default=[]),
    released_from: date | None = None,
    released_to: date | None = None,
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SearchResponse:
    statement = select(DataModel)
    if q:
        needle = f"%{q}%"
        statement = statement.where(or_(DataModel.title.ilike(needle), DataModel.description.ilike(needle)))
    if license:
        statement = statement.where(DataModel.license.in_(license))
    for value in domain:
        statement = statement.where(DataModel.domains.contains([value]))
    if released_from:
        statement = statement.where(DataModel.updated_at >= datetime.combine(released_from, time.min))
    if released_to:
        statement = statement.where(DataModel.updated_at <= datetime.combine(released_to, time.max))

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    order_by = [DataModel.updated_at.desc().nullslast()]
    if q:
        needle = f"%{q}%"
        order_by = [
            case((DataModel.title.ilike(needle), 0), else_=1),
            DataModel.updated_at.desc().nullslast(),
        ]
    items = db.scalars(statement.order_by(*order_by).limit(limit).offset(offset)).all()

    all_models = db.scalars(select(DataModel)).all()
    licenses = _facet_counts([item.license for item in all_models if item.license])
    domains = _facet_counts([domain for item in all_models for domain in item.domains])
    return SearchResponse(items=items, total=total, licenses=licenses, domains=domains)


@router.get("/datamodels/{datamodel_id}", response_model=DataModelDetail)
def get_datamodel(datamodel_id: int, db: Session = Depends(get_db)) -> DataModel:
    datamodel = db.scalar(
        select(DataModel)
        .where(DataModel.id == datamodel_id)
        .options(selectinload(DataModel.versions).selectinload(ModelVersion.layers))
    )
    if datamodel is None:
        raise HTTPException(status_code=404, detail="Datamodel not found")
    datamodel.versions.sort(key=lambda version: version.release_date or datetime.min, reverse=True)
    return datamodel


@router.post("/admin/sync")
async def sync_now(
    x_admin_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    if sync_lock.locked():
        raise HTTPException(status_code=409, detail="A sync is already running")
    try:
        async with sync_lock:
            return await SyncService(settings).sync(db)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OCI registry returned {exc.response.status_code} for {exc.request.url}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Could not reach OCI registry: {exc}") from exc
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail=f"Database operation failed: {exc.orig}") from exc


@router.get("/admin/debug")
async def debug_status(
    x_admin_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    result: dict = {
        "database_url": _mask_database_url(settings.database_url),
        "registry_url": settings.registry_base_url,
        "username_configured": bool(settings.oci_username),
        "username_contains_dollar": "$" in (settings.oci_username or ""),
        "username_length": len(settings.oci_username or ""),
        "password_configured": bool(settings.oci_password),
        "allowlist_patterns": settings.allowlist_patterns,
        "sync_interval_minutes": settings.sync_interval_minutes,
        "sync_on_startup": settings.sync_on_startup,
        "sync_running": sync_lock.locked(),
        "sync_status": sync_state.as_dict(),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(f"{settings.registry_base_url}/v2/", auth=_auth(settings))
        result["registry_probe"] = {
            "status_code": response.status_code,
            "auth_challenge": response.headers.get("WWW-Authenticate"),
        }
    except httpx.RequestError as exc:
        result["registry_probe"] = {"error": str(exc)}
    return result


@router.get("/admin/sync/status")
def sync_status(
    x_admin_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    latest_run = db.scalar(select(SyncRun).order_by(SyncRun.started_at.desc(), SyncRun.id.desc()))
    result = sync_state.as_dict()
    if latest_run is None:
        result["persisted_run"] = None
        return result

    current_repository = db.scalar(
        select(SyncRepositoryState.repository)
        .where(SyncRepositoryState.run_id == latest_run.id, SyncRepositoryState.status == "syncing")
        .order_by(SyncRepositoryState.started_at.desc())
    )
    result["persisted_run"] = {
        "id": latest_run.id,
        "status": latest_run.status,
        "started_at": latest_run.started_at,
        "finished_at": latest_run.finished_at,
        "total_repositories": latest_run.total_repositories,
        "synced_repositories": latest_run.synced_repositories,
        "failed_repositories": latest_run.failed_repositories,
        "current_repository": current_repository,
        "error": latest_run.error,
    }
    return result


@router.get("/datamodels/{datamodel_id}/layers/{digest:path}/download")
async def download_layer(
    datamodel_id: int,
    digest: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    layer = db.scalar(
        select(ModelLayer)
        .join(ModelVersion)
        .join(DataModel)
        .where(DataModel.id == datamodel_id, ModelLayer.digest == digest)
        .options(selectinload(ModelLayer.version).selectinload(ModelVersion.datamodel))
    )
    if layer is None:
        raise HTTPException(status_code=404, detail="Layer not found")

    client = OCIClient(settings.registry_base_url, settings.oci_username, settings.oci_password)
    _, stream = await client.stream_blob(layer.version.datamodel.repository, digest)
    return StreamingResponse(stream, media_type=layer.media_type)


def _facet_counts(values: list[str]) -> list[FacetValue]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return [FacetValue(value=value, count=count) for value, count in sorted(counts.items())]


def _auth(settings: Settings) -> tuple[str, str] | None:
    if settings.oci_username and settings.oci_password:
        return settings.oci_username, settings.oci_password
    return None


def _mask_database_url(value: str) -> str:
    if "://" not in value or "@" not in value:
        return value
    scheme, rest = value.split("://", 1)
    return f"{scheme}://***@{rest.split('@', 1)[1]}"
