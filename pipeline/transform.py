"""Transform: pure function, raw DataFrame in, clean DataFrame out. No I/O.

Source quirks handled here (checked against the live dataset, Nov 2026):
- Most state-months have two rows: a preliminary report (final_report = "N")
  and an updated one (final_report = "Y"), often with different totals. The
  updated row is kept when both exist; the newest month has a preliminary row only.
- The API returns every value as a string or null, with snake_case column
  names. The CSV has title-case headers and gives reporting_period as an integer.
"""

import pandas as pd

COLUMN_MAP = {  # source name -> our name
    "state_abbreviation": "state_code",
    "reporting_period": "report_month",
    "total_medicaid_and_chip_enrollment": "total_enrollment",
    "total_medicaid_enrollment": "medicaid_enrollment",
    "total_chip_enrollment": "chip_enrollment",
}
COUNT_COLS = ["total_enrollment", "medicaid_enrollment", "chip_enrollment"]
KEY_COLS = ["state_code", "report_month"]
FINAL_FLAG = "final_report"  # "Y" on the updated row, "N" on the preliminary one


def _normalise(name) -> str:
    return str(name).strip().lower().replace(" ", "_")


def transform(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=_normalise)

    missing = [c for c in COLUMN_MAP if c not in df.columns]
    if missing:
        raise KeyError(f"source is missing expected columns: {missing}")

    out = df[list(COLUMN_MAP)].rename(columns=COLUMN_MAP).copy()

    out["state_code"] = out["state_code"].astype("string").str.strip().str.upper()

    # Cast to text first so "201309" (API) and 201309 (CSV) parse the same way.
    out["report_month"] = pd.to_datetime(
        out["report_month"].astype("string").str.strip(), format="%Y%m", errors="coerce"
    )

    for c in COUNT_COLS:
        text = out[c].astype("string").str.replace(",", "", regex=False)
        out[c] = pd.to_numeric(text, errors="coerce").astype("Int64")

    # One row per state and month, preferring the updated report over the
    # preliminary one. Sorting on the flag (stably) puts updated rows last,
    # so the choice does not depend on the order the source returns rows in.
    if FINAL_FLAG in df.columns:
        is_final = df[FINAL_FLAG].astype("string").str.strip().str.upper().eq("Y")
        out["_is_final"] = is_final.fillna(False).astype(bool)
    else:
        out["_is_final"] = False

    out = (
        out.sort_values("_is_final", kind="stable")
        .drop_duplicates(subset=KEY_COLS, keep="last")
        .drop(columns="_is_final")
        .sort_values(KEY_COLS)
        .reset_index(drop=True)
    )
    return out
