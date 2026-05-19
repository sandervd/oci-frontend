from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    digest: str
    media_type: str
    size: int | None = None
    annotations: dict = Field(default_factory=dict)


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tag: str
    version: str | None = None
    digest: str | None = None
    title: str
    description: str
    license: str | None = None
    domains: list[str]
    release_date: datetime | None = None
    media_type: str | None = None
    annotations: dict = Field(default_factory=dict)
    adms: dict | list | str | None = None
    layers: list[LayerRead] = Field(default_factory=list)


class DataModelSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository: str
    title: str
    description: str
    license: str | None = None
    domains: list[str]
    latest_tag: str | None = None
    updated_at: datetime | None = None


class DataModelDetail(DataModelSummary):
    latest_digest: str | None = None
    versions: list[VersionRead]


class FacetValue(BaseModel):
    value: str
    count: int


class SearchResponse(BaseModel):
    items: list[DataModelSummary]
    total: int
    licenses: list[FacetValue]
    domains: list[FacetValue]
