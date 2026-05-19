from contextlib import asynccontextmanager
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.services.sync import SyncService
from app.services.sync_lock import sync_lock
from app.services.sync_state import sync_state


settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)


async def run_sync() -> None:
    if sync_lock.locked():
        logger.info("Skipping scheduled OCI sync because another sync is already running")
        return
    db = SessionLocal()
    try:
        async with sync_lock:
            await SyncService(settings).sync(db)
    except Exception as exc:
        sync_state.fail(exc)
        logger.warning("OCI registry sync failed: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler.add_job(run_sync, "interval", minutes=settings.sync_interval_minutes, id="oci-sync", replace_existing=True)
    scheduler.start()
    if settings.sync_on_startup:
        scheduler.add_job(run_sync, id="startup-sync", replace_existing=True)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Semantic registry of data models", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
