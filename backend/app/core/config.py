from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/registry.db"
    oci_registry_url: str = "https://harbor.example.eu"
    oci_username: str | None = None
    oci_password: str | None = None
    oci_allowlist: str = "*"
    sync_interval_minutes: int = 60
    sync_on_startup: bool = True
    admin_token: str = "change-me"
    frontend_origins: str = "http://localhost:5173"

    @property
    def registry_base_url(self) -> str:
        return self.oci_registry_url.rstrip("/")

    @property
    def allowlist_patterns(self) -> list[str]:
        return [item.strip() for item in self.oci_allowlist.split(",") if item.strip()]

    @property
    def frontend_origin_list(self) -> list[str]:
        return [item.strip() for item in self.frontend_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
