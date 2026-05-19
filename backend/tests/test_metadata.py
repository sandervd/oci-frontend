import json
from pathlib import Path

from app.services.metadata import choose_latest, parse_multi_value, summarize


def test_summarize_standard_and_custom_annotations():
    manifest = json.loads(Path("tests/fixtures/oci_manifest.json").read_text())

    result = summarize("semantic/address-model", "1.2.0", manifest)

    assert result["title"] == "Address Data Model"
    assert result["license"] == "CC-BY-4.0"
    assert result["domains"] == ["location", "public-administration"]
    assert result["release_date"].year == 2026
    assert len(result["layers"]) == 2


def test_multi_value_accepts_json_and_csv():
    assert parse_multi_value('["energy", "transport"]') == ["energy", "transport"]
    assert parse_multi_value("energy, transport") == ["energy", "transport"]


def test_choose_latest_prefers_latest_annotation_date():
    latest = choose_latest(
        [
            {"tag": "2.0.0", "release_date": None},
            {"tag": "latest", "release_date": summarize("repo", "latest", json.loads(Path("tests/fixtures/oci_manifest.json").read_text()))["release_date"]},
        ]
    )

    assert latest["tag"] == "latest"


def test_choose_latest_uses_semver_when_all_non_latest_are_semver():
    latest = choose_latest(
        [
            {"tag": "1.0.0", "release_date": None},
            {"tag": "1.10.0", "release_date": None},
            {"tag": "1.2.0", "release_date": None},
        ]
    )

    assert latest["tag"] == "1.10.0"
