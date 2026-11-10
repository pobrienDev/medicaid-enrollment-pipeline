"""Integration tests for load, against a real Postgres (see the engine fixture)."""

import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from pipeline.load import load


def count(engine) -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT count(*) FROM enrollment")).scalar()


def fetch_row(engine, state, month):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT total_enrollment, medicaid_enrollment, chip_enrollment "
                "FROM enrollment WHERE state_code = :s AND report_month = :m"
            ),
            {"s": state, "m": month},
        ).one()


def test_rows_land(engine, clean_df):
    loaded = load(clean_df, engine)

    assert loaded == len(clean_df)
    assert count(engine) == len(clean_df)
    assert fetch_row(engine, "MD", datetime.date(2026, 6, 1)) == (1_394_806, 1_195_440, 199_366)


def test_load_is_idempotent(engine, clean_df):
    load(clean_df, engine)
    load(clean_df, engine)

    assert count(engine) == len(clean_df)


def test_updated_values_overwrite(engine, clean_df):
    load(clean_df, engine)

    revised = clean_df.copy()
    is_md_june = (revised["state_code"] == "MD") & (revised["report_month"] == "2026-06-01")
    revised.loc[is_md_june, "total_enrollment"] = 1_400_000
    load(revised, engine)

    assert count(engine) == len(clean_df)
    assert fetch_row(engine, "MD", datetime.date(2026, 6, 1)).total_enrollment == 1_400_000


def test_missing_counts_are_stored_as_null(engine, clean_df):
    load(clean_df, engine)

    row = fetch_row(engine, "AK", datetime.date(2013, 9, 1))
    assert row.total_enrollment == 122_334
    assert row.medicaid_enrollment is None
    assert row.chip_enrollment is None


def test_report_month_is_stored_as_a_date(engine, clean_df):
    load(clean_df, engine)

    with engine.connect() as conn:
        latest = conn.execute(text("SELECT max(report_month) FROM enrollment")).scalar()
    assert latest == datetime.date(2026, 7, 1)


def test_failed_load_changes_nothing(engine, clean_df):
    load(clean_df, engine)

    # A negative count slips past the caller but violates the table's CHECK
    # constraint. The whole load must roll back, including the good rows.
    bad = clean_df.copy()
    bad.loc[bad.index[0], "total_enrollment"] = -1
    bad.loc[bad.index[1], "total_enrollment"] = 999
    untouched = bad.iloc[1]

    with pytest.raises(IntegrityError):
        load(bad, engine)

    assert count(engine) == len(clean_df)
    stored = fetch_row(engine, untouched["state_code"], untouched["report_month"].date())
    assert stored.total_enrollment != 999
