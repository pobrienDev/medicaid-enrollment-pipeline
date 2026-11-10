"""Unit tests for transform.

The fixture has the awkward cases: AK 2013-09 (updated only, blank Medicaid
and CHIP counts), preliminary/updated pairs with different totals, and
2026-07 rows that are preliminary only.
"""

import pandas as pd
import pytest

from pipeline.transform import COLUMN_MAP, COUNT_COLS, transform


def api_row(**overrides) -> dict:
    """One row shaped like the API returns it: snake_case names, string values."""
    row = {
        "state_abbreviation": "MD",
        "reporting_period": "202601",
        "preliminary_or_updated": "U",
        "final_report": "Y",
        "total_medicaid_and_chip_enrollment": "1500",
        "total_medicaid_enrollment": "1200",
        "total_chip_enrollment": "300",
    }
    row.update(overrides)
    return row


def value(df, state, month, column):
    match = df[(df["state_code"] == state) & (df["report_month"] == pd.Timestamp(month))]
    assert len(match) == 1, f"expected one row for {state} {month}, got {len(match)}"
    return match.iloc[0][column]


def test_output_has_exactly_the_mapped_columns(clean_df):
    assert list(clean_df.columns) == list(COLUMN_MAP.values())


def test_fixture_collapses_to_one_row_per_state_and_month(raw_df, clean_df):
    assert len(raw_df) == 20
    assert len(clean_df) == 13
    assert not clean_df.duplicated(subset=["state_code", "report_month"]).any()


def test_updated_row_wins_over_preliminary(clean_df):
    # MD 2026-06: preliminary 1,385,888, updated 1,394,806
    assert value(clean_df, "MD", "2026-06-01", "total_enrollment") == 1_394_806
    assert value(clean_df, "MD", "2026-06-01", "chip_enrollment") == 199_366


def test_updated_row_wins_whatever_order_the_source_uses():
    updated = api_row(total_medicaid_and_chip_enrollment="200")
    preliminary = api_row(
        preliminary_or_updated="P", final_report="N", total_medicaid_and_chip_enrollment="100"
    )

    for rows in ([preliminary, updated], [updated, preliminary]):
        out = transform(pd.DataFrame(rows))
        assert len(out) == 1
        assert out.iloc[0]["total_enrollment"] == 200


def test_preliminary_only_month_is_kept(clean_df):
    assert value(clean_df, "MD", "2026-07-01", "total_enrollment") == 1_386_943


def test_dates_parse_from_csv_integers(clean_df):
    assert str(clean_df["report_month"].dtype).startswith("datetime64")
    assert clean_df["report_month"].min() == pd.Timestamp("2013-09-01")
    assert clean_df["report_month"].max() == pd.Timestamp("2026-07-01")


def test_dates_parse_from_api_strings():
    out = transform(pd.DataFrame([api_row(reporting_period="201309")]))

    assert out.iloc[0]["report_month"] == pd.Timestamp("2013-09-01")


def test_unparseable_date_becomes_nat_for_validation_to_catch():
    out = transform(pd.DataFrame([api_row(reporting_period="Sept 2013")]))

    assert out["report_month"].isna().all()


def test_commas_in_numbers_are_handled():
    out = transform(pd.DataFrame([api_row(total_medicaid_and_chip_enrollment="1,234,567")]))

    assert out.iloc[0]["total_enrollment"] == 1_234_567


def test_counts_are_nullable_integers(clean_df):
    for c in COUNT_COLS:
        assert str(clean_df[c].dtype) == "Int64"
    # AK 2013-09 has a total but blank Medicaid and CHIP counts
    assert value(clean_df, "AK", "2013-09-01", "total_enrollment") == 122_334
    assert pd.isna(value(clean_df, "AK", "2013-09-01", "medicaid_enrollment"))
    assert pd.isna(value(clean_df, "AK", "2013-09-01", "chip_enrollment"))


def test_api_nulls_become_missing_counts():
    out = transform(pd.DataFrame([api_row(total_medicaid_enrollment=None)]))

    assert pd.isna(out.iloc[0]["medicaid_enrollment"])
    assert out.iloc[0]["chip_enrollment"] == 300


def test_state_codes_are_stripped_and_uppercased():
    out = transform(pd.DataFrame([api_row(state_abbreviation=" md ")]))

    assert out.iloc[0]["state_code"] == "MD"


def test_csv_and_api_shapes_give_the_same_result(raw_df, clean_df):
    # Rebuild the fixture the way the API serves it: snake_case names, all strings.
    api_like = raw_df.rename(columns=lambda c: c.strip().lower().replace(" ", "_"))
    api_like = api_like.astype("string")

    pd.testing.assert_frame_equal(transform(api_like), clean_df)


def test_missing_source_column_raises():
    raw = pd.DataFrame([api_row()]).drop(columns="total_chip_enrollment")

    with pytest.raises(KeyError, match="total_chip_enrollment"):
        transform(raw)


def test_input_is_not_modified(raw_df):
    before = raw_df.copy()

    transform(raw_df)

    pd.testing.assert_frame_equal(raw_df, before)
