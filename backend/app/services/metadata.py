import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from packaging.version import InvalidVersion, Version

TITLE = "org.opencontainers.image.title"
DESCRIPTION = "org.opencontainers.image.description"
CREATED = "org.opencontainers.image.created"
VERSION = "org.opencontainers.image.version"
LICENSE = "org.opencontainers.image.licenses"
DOMAIN = "eu.europa.publications.datamodel.domain"
ADMS = "eu.europa.publications.datamodel.adms"


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_jsonish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def parse_multi_value(value: Any) -> list[str]:
    parsed = parse_jsonish(value)
    if parsed is None:
        return []
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, str):
        return [item.strip() for item in parsed.split(",") if item.strip()]
    return [str(parsed)]


def extract_annotations(manifest: dict, config_blob: dict | None = None) -> dict:
    annotations = {}
    annotations.update(config_blob.get("config", {}).get("Labels", {}) if config_blob else {})
    annotations.update(config_blob.get("annotations", {}) if config_blob else {})
    annotations.update(manifest.get("annotations", {}) or {})
    return annotations


def summarize(repository: str, tag: str, manifest: dict, config_blob: dict | None = None) -> dict:
    annotations = extract_annotations(manifest, config_blob)
    title = annotations.get(TITLE) or repository.split("/")[-1].replace("-", " ").replace("_", " ").title()
    description = annotations.get(DESCRIPTION) or ""
    release_date = parse_datetime(annotations.get(CREATED))
    return {
        "tag": tag,
        "version": annotations.get(VERSION),
        "title": title,
        "description": description,
        "license": annotations.get(LICENSE),
        "domains": parse_multi_value(annotations.get(DOMAIN)),
        "release_date": release_date,
        "annotations": annotations,
        "adms": parse_jsonish(annotations.get(ADMS)),
        "media_type": manifest.get("mediaType"),
        "layers": manifest.get("layers", []),
    }


def choose_latest(versions: list[dict]) -> dict | None:
    if not versions:
        return None
    by_tag = {version["tag"]: version for version in versions}
    latest_tag = by_tag.get("latest")
    if latest_tag and latest_tag.get("release_date"):
        return latest_tag

    non_latest = [version for version in versions if version["tag"] != "latest"]
    semver_versions = []
    for version in non_latest:
        try:
            semver_versions.append((Version(version["tag"].removeprefix("v")), version))
        except InvalidVersion:
            semver_versions = []
            break
    if semver_versions and len(semver_versions) == len(non_latest):
        return sorted(semver_versions, key=lambda item: item[0])[-1][1]

    dated = [version for version in versions if version.get("release_date")]
    if dated:
        return sorted(dated, key=lambda version: normalize_datetime(version["release_date"]))[-1]
    return sorted(versions, key=lambda version: version["tag"])[-1]


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
