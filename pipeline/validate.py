"""Validate: data-quality gate that runs before anything is written. No I/O."""

import pandas as pd

COUNT_COLS = ["total_enrollment", "medicaid_enrollment", "chip_enrollment"]
KEY_COLS = ["state_code", "report_month"]


class ValidationError(Exception):
    pass


def validate(df: pd.DataFrame) -> None:
    """Collect every problem, then raise once so a failed run reports them all."""
    problems = []

    if df.empty:
        problems.append("no rows")

    bad_dates = int(df["report_month"].isna().sum())
    if bad_dates:
        problems.append(f"{bad_dates} unparseable dates")

    # A missing state code is as bad as a malformed one.
    codes_ok = df["state_code"].str.fullmatch(r"[A-Z]{2}").fillna(False).astype(bool)
    if not codes_ok.all():
        problems.append(f"{int((~codes_ok).sum())} bad state codes")

    for c in COUNT_COLS:
        if (df[c] < 0).any():
            problems.append(f"negative values in {c}")

    # The upsert needs exactly one row per key; duplicates would abort the load.
    dupes = int(df.duplicated(subset=KEY_COLS).sum())
    if dupes:
        problems.append(f"{dupes} duplicate state/month rows")

    if problems:
        raise ValidationError("; ".join(problems))
