"""Download the source dataset from data.gouv.fr / La Poste and record fetch metadata.

Source: "Base officielle des codes postaux" (La Poste / data.gouv.fr).
License: Licence Ouverte v2.0 (Etalab) - free reuse with attribution.
Dataset page: https://www.data.gouv.fr/fr/datasets/base-officielle-des-codes-postaux/
Raw resource: https://data.laposte.fr/data-fair/api/v1/datasets/laposte-hexasmal/raw

Why this dataset: real, official, French, updated regularly (communes and
postal codes change over time as INSEE codes get merged/split), large enough
(~39k rows) to make completeness/uniqueness/referential checks meaningful.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

SOURCE_URL = "https://data.laposte.fr/data-fair/api/v1/datasets/laposte-hexasmal/raw"
DATASET_PAGE = "https://www.data.gouv.fr/fr/datasets/base-officielle-des-codes-postaux/"
LICENSE = "Licence Ouverte v2.0 (Etalab)"

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_FILE = RAW_DIR / "codes_postaux.csv"
METADATA_FILE = RAW_DIR / "metadata.json"


def fetch() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    response = requests.get(SOURCE_URL, timeout=60)
    response.raise_for_status()
    RAW_FILE.write_bytes(response.content)

    metadata = {
        "source_url": SOURCE_URL,
        "dataset_page": DATASET_PAGE,
        "license": LICENSE,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": len(response.content),
    }
    METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Fetched {len(response.content)} bytes -> {RAW_FILE}")
    print(f"Metadata -> {METADATA_FILE}")


if __name__ == "__main__":
    fetch()
