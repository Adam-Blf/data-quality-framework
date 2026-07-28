"""Unit tests for the custom (non-GX) quality checks, run against synthetic
in-memory data so they never depend on network access or the real dataset."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_and_run_suite as suite  # noqa: E402


def make_frame(rows):
    return pd.DataFrame(
        rows,
        columns=["code_commune_insee", "nom_commune", "code_postal", "libelle_acheminement", "ligne_5"],
    )


def test_referential_consistency_passes_on_clean_data():
    df = make_frame(
        [
            ["01001", "COMMUNE A", "01400", "COMMUNE A", None],
            ["75056", "PARIS", "75001", "PARIS 1", None],
            ["2A004", "AJACCIO", "20000", "AJACCIO", None],
            ["99138", "MONACO", "98000", "MONACO", None],
        ]
    )
    report = suite.referential_consistency_report(df)
    assert report["passed"] is True
    assert report["invalid_rows"] == 0


def test_referential_consistency_fails_on_unknown_department_prefix():
    df = make_frame(
        [
            ["01001", "COMMUNE A", "01400", "COMMUNE A", None],
            ["00000", "NOWHERE", "00999", "NOWHERE", None],
        ]
    )
    report = suite.referential_consistency_report(df)
    assert report["passed"] is False
    assert report["invalid_rows"] == 1


def test_freshness_passes_when_recent(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    metadata_path = tmp_path / "data" / "raw" / "metadata.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        json.dumps({"fetched_at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8"
    )
    monkeypatch.setattr(suite, "ROOT", tmp_path)
    report = suite.freshness_report(max_staleness_days=180)
    assert report["passed"] is True


def test_freshness_fails_when_stale(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone

    metadata_path = tmp_path / "data" / "raw" / "metadata.json"
    metadata_path.parent.mkdir(parents=True)
    old_date = datetime.now(timezone.utc) - timedelta(days=400)
    metadata_path.write_text(json.dumps({"fetched_at": old_date.isoformat()}), encoding="utf-8")
    monkeypatch.setattr(suite, "ROOT", tmp_path)
    report = suite.freshness_report(max_staleness_days=180)
    assert report["passed"] is False


def test_freshness_fails_when_metadata_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(suite, "ROOT", tmp_path)
    report = suite.freshness_report()
    assert report["passed"] is False
