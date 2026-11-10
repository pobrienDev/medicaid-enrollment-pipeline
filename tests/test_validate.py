"""Unit tests for validate."""

import pandas as pd
import pytest

from pipeline.validate import ValidationError, validate


def test_clean_data_passes(clean_df):
    validate(clean_df)  # does not raise


def test_missing_counts_are_allowed(clean_df):
    # The fixture includes a row with blank Medicaid and CHIP counts.
    assert clean_df["medicaid_enrollment"].isna().any()
    validate(clean_df)


def test_empty_frame_raises(clean_df):
    with pytest.raises(ValidationError, match="no rows"):
        validate(clean_df.iloc[0:0])


def test_bad_dates_raise(clean_df):
    df = clean_df.copy()
    df.loc[df.index[:2], "report_month"] = pd.NaT

    with pytest.raises(ValidationError, match="2 unparseable dates"):
        validate(df)


@pytest.mark.parametrize("bad_code", ["Maryland", "md", "M1", "", None])
def test_bad_state_codes_raise(clean_df, bad_code):
    df = clean_df.copy()
    df.loc[df.index[0], "state_code"] = bad_code

    with pytest.raises(ValidationError, match="1 bad state codes"):
        validate(df)


@pytest.mark.parametrize("column", ["total_enrollment", "medicaid_enrollment", "chip_enrollment"])
def test_negative_counts_raise(clean_df, column):
    df = clean_df.copy()
    df.loc[df.index[0], column] = -1

    with pytest.raises(ValidationError, match=f"negative values in {column}"):
        validate(df)


def test_duplicate_keys_raise(clean_df):
    df = pd.concat([clean_df, clean_df.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValidationError, match="1 duplicate state/month rows"):
        validate(df)


def test_all_problems_are_reported_together(clean_df):
    df = clean_df.copy()
    df.loc[df.index[0], "state_code"] = "Maryland"
    df.loc[df.index[1], "chip_enrollment"] = -5

    with pytest.raises(ValidationError) as excinfo:
        validate(df)

    message = str(excinfo.value)
    assert "bad state codes" in message
    assert "negative values in chip_enrollment" in message
