"""Load and lightly normalise the codes-postaux dataset for validation.

The source CSV is semicolon-separated, Latin-1 encoded (as published by La
Poste). Column names are renamed to clean, ASCII, snake_case identifiers so
expectation suites stay readable; no values are altered.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "raw" / "codes_postaux.csv"

COLUMN_RENAME = {
    "#Code_commune_INSEE": "code_commune_insee",
    "Code_commune_INSEE": "code_commune_insee",
    "Nom_de_la_commune": "nom_commune",
    "Code_postal": "code_postal",
    "Libell\xe9_d_acheminement": "libelle_acheminement",
    "Ligne_5": "ligne_5",
}

EXPECTED_COLUMNS = [
    "code_commune_insee",
    "nom_commune",
    "code_postal",
    "libelle_acheminement",
    "ligne_5",
]


def load(csv_path: Path = DEFAULT_CSV) -> pd.DataFrame:
    df = pd.read_csv(
        csv_path,
        sep=";",
        encoding="latin-1",
        dtype=str,
    )
    df = df.rename(columns=COLUMN_RENAME)
    return df


if __name__ == "__main__":
    frame = load()
    print(frame.shape)
    print(frame.columns.tolist())
