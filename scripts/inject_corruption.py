"""Demo helper: corrupt a copy of the dataset on purpose to prove the quality
gate actually fails. Never run against the canonical data/raw file used by CI.

Usage:
    python scripts/inject_corruption.py            # writes data/raw/codes_postaux.csv (corrupted)
    python scripts/inject_corruption.py --restore   # re-downloads the clean file
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_data import DEFAULT_CSV  # noqa: E402

BACKUP_PATH = DEFAULT_CSV.with_suffix(".csv.bak")


def corrupt() -> None:
    if not BACKUP_PATH.exists():
        shutil.copy(DEFAULT_CSV, BACKUP_PATH)

    df = pd.read_csv(DEFAULT_CSV, sep=";", encoding="latin-1", dtype=str)

    # 1) Break completeness: null out a batch of postal codes.
    df.loc[df.index[:50], "Code_postal"] = None
    # 2) Break the format/range expectation: inject clearly invalid postal codes.
    df.loc[df.index[50:55], "Code_postal"] = ["ABCDE", "0000", "999999", "12", "PARIS"]
    # 3) Break referential consistency: a postal code with a department prefix
    #    that does not exist (department "00" is not a real French department).
    df.loc[df.index[55], "Code_postal"] = "00999"
    # 4) Break schema drift detection: rename a column outright.
    df = df.rename(columns={"Nom_de_la_commune": "Nom_Commune_RENAMED"})

    df.to_csv(DEFAULT_CSV, sep=";", encoding="latin-1", index=False)
    print(f"Injected corruption into {DEFAULT_CSV}")
    print("Run `python scripts/build_and_run_suite.py` now: it must exit non-zero.")


def restore() -> None:
    if BACKUP_PATH.exists():
        shutil.copy(BACKUP_PATH, DEFAULT_CSV)
        BACKUP_PATH.unlink()
        print(f"Restored clean dataset to {DEFAULT_CSV}")
    else:
        print("No backup found, run scripts/fetch_data.py to get a clean copy.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    restore() if args.restore else corrupt()
