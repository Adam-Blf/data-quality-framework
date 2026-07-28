"""Build the Great Expectations suite for the codes-postaux dataset, run it,
generate HTML Data Docs, and exit non-zero when quality thresholds are breached.

This is the single entry point used both locally and in CI
(`make validate` / `python scripts/build_and_run_suite.py`).
"""
from __future__ import annotations

import sys
from pathlib import Path

import great_expectations as gx
from great_expectations.checkpoint import Checkpoint
from great_expectations.exceptions.exceptions import DataContextError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_data import DEFAULT_CSV, EXPECTED_COLUMNS, load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"

DATASOURCE_NAME = "codes_postaux_source"
ASSET_NAME = "codes_postaux_asset"
BATCH_DEF_NAME = "codes_postaux_full_table"
SUITE_NAME = "codes_postaux_suite"
CHECKPOINT_NAME = "codes_postaux_checkpoint"

# Departement codes are the first two digits of the commune INSEE code, with
# a handful of documented exceptions (Corsica uses 2A/2B, and DOM communes
# use 971-976). Valid postal-code prefixes mirror this same range.
# 98 is a documented, accepted exception: Monaco (commune INSEE 99138) is a
# sovereign foreign state but is delivered by the French postal network under
# its own "98000" prefix, so it legitimately appears in this French dataset.
VALID_DEPARTMENT_PREFIXES = {f"{i:02d}" for i in range(1, 96)} | {"2A", "2B", "98"} | {
    "971", "972", "973", "974", "975", "976", "977", "978", "984", "986", "987", "988"
}


def get_context() -> gx.data_context.data_context.file_data_context.FileDataContext:
    return gx.get_context(mode="file", project_root_dir=str(ROOT))


def get_or_add_datasource(context):
    try:
        return context.data_sources.get(DATASOURCE_NAME)
    except (KeyError, LookupError, DataContextError):
        return context.data_sources.add_pandas(DATASOURCE_NAME)


def get_or_add_asset(datasource):
    try:
        return datasource.get_asset(ASSET_NAME)
    except LookupError:
        return datasource.add_dataframe_asset(name=ASSET_NAME)


def get_or_add_batch_definition(asset):
    try:
        return asset.get_batch_definition(BATCH_DEF_NAME)
    except LookupError:
        return asset.add_batch_definition_whole_dataframe(BATCH_DEF_NAME)


def build_suite(context) -> gx.ExpectationSuite:
    try:
        suite = context.suites.get(SUITE_NAME)
        suite.expectations = []
    except (KeyError, LookupError, DataContextError):
        suite = gx.ExpectationSuite(name=SUITE_NAME)

    expectations = [
        # --- Completeness -----------------------------------------------
        gx.expectations.ExpectColumnValuesToNotBeNull(column="code_commune_insee"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="nom_commune"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="code_postal"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="libelle_acheminement"),
        # --- Uniqueness ---------------------------------------------------
        # IMPORTANT real-world finding: `code_commune_insee` alone is NOT a
        # unique key in this file (4185 duplicates observed) because large
        # communes are split across several delivery/routing lines (one row
        # per hamlet or postal sector). The true grain of one row is the full
        # delivery record, so uniqueness is checked on the whole row instead.
        gx.expectations.ExpectCompoundColumnsToBeUnique(column_list=EXPECTED_COLUMNS),
        # --- Value ranges / format -----------------------------------------
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="code_postal", regex=r"^[0-9]{5}$"
        ),
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="code_commune_insee", regex=r"^(2A|2B|[0-9]{2,3})[0-9A-Z]{2,3}$"
        ),
        gx.expectations.ExpectColumnValueLengthsToEqual(
            column="code_postal", value=5
        ),
        # --- Schema drift ---------------------------------------------------
        gx.expectations.ExpectTableColumnsToMatchSet(
            column_set=EXPECTED_COLUMNS, exact_match=True
        ),
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=30000, max_value=45000),
    ]
    for expectation in expectations:
        suite.add_expectation(expectation)

    context.suites.add_or_update(suite)
    return suite


def referential_consistency_report(df) -> dict:
    """Custom check: postal-code department prefix must be a real department.

    This is not expressible as a single built-in GX expectation (it needs a
    derived column), so it is run as a companion Python check and folded
    into the same pass/fail decision as the GX suite.
    """
    prefixes = df["code_postal"].str.slice(0, 2)
    prefixes_3 = df["code_postal"].str.slice(0, 3)
    is_dom = prefixes_3.isin({p for p in VALID_DEPARTMENT_PREFIXES if len(p) == 3})
    is_metro_or_corse = prefixes.isin(VALID_DEPARTMENT_PREFIXES)
    valid = is_dom | is_metro_or_corse
    invalid_count = int((~valid).sum())
    return {
        "check": "postal_code_department_prefix_consistency",
        "invalid_rows": invalid_count,
        "total_rows": int(len(df)),
        "passed": invalid_count == 0,
    }


def freshness_report(max_staleness_days: int | None = None) -> dict:
    import json
    import os
    from datetime import datetime, timezone

    if max_staleness_days is None:
        max_staleness_days = int(os.environ.get("MAX_STALENESS_DAYS", "180"))

    metadata_path = ROOT / "data" / "raw" / "metadata.json"
    if not metadata_path.exists():
        return {"check": "freshness", "passed": False, "reason": "metadata.json missing, run fetch_data.py"}

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    fetched_at = datetime.fromisoformat(metadata["fetched_at"])
    age_days = (datetime.now(timezone.utc) - fetched_at).days
    return {
        "check": "freshness",
        "fetched_at": metadata["fetched_at"],
        "age_days": age_days,
        "max_staleness_days": max_staleness_days,
        "passed": age_days <= max_staleness_days,
    }


def run() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df = load(DEFAULT_CSV)

    context = get_context()
    datasource = get_or_add_datasource(context)
    asset = get_or_add_asset(datasource)
    batch_definition = get_or_add_batch_definition(asset)
    suite = build_suite(context)

    try:
        validation_definition = context.validation_definitions.get(SUITE_NAME)
    except (KeyError, LookupError, DataContextError):
        validation_definition = gx.ValidationDefinition(
            name=SUITE_NAME, data=batch_definition, suite=suite
        )
        validation_definition = context.validation_definitions.add(validation_definition)

    try:
        checkpoint = context.checkpoints.get(CHECKPOINT_NAME)
    except (KeyError, LookupError, DataContextError):
        checkpoint = Checkpoint(
            name=CHECKPOINT_NAME,
            validation_definitions=[validation_definition],
            actions=[gx.checkpoint.UpdateDataDocsAction(name="update_data_docs")],
        )
        checkpoint = context.checkpoints.add(checkpoint)

    result = checkpoint.run(batch_parameters={"dataframe": df})

    context.build_data_docs()

    gx_success = bool(result.success)

    ref_check = referential_consistency_report(df)
    fresh_check = freshness_report()

    all_passed = gx_success and ref_check["passed"] and fresh_check["passed"]

    print("=" * 70)
    print(f"Great Expectations checkpoint success: {gx_success}")
    print(f"Referential consistency check: {ref_check}")
    print(f"Freshness check: {fresh_check}")
    print("=" * 70)
    print(f"Data Docs generated under: {ROOT / 'gx' / 'uncommitted' / 'data_docs'}")

    if not all_passed:
        print("QUALITY GATE FAILED: at least one check did not pass.", file=sys.stderr)
        return 1

    print("QUALITY GATE PASSED: all checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
