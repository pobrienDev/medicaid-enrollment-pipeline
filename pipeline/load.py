"""Load: staging table + idempotent upsert in one transaction. Does I/O."""

import pandas as pd
from sqlalchemy import Date, Integer, Text, text
from sqlalchemy.engine import Engine

STAGING_TABLE = "staging_enrollment"

STAGING_TYPES = {
    "state_code": Text(),
    "report_month": Date(),
    "total_enrollment": Integer(),
    "medicaid_enrollment": Integer(),
    "chip_enrollment": Integer(),
}

UPSERT = text("""
    INSERT INTO enrollment (state_code, report_month, total_enrollment,
                            medicaid_enrollment, chip_enrollment)
    SELECT state_code, report_month, total_enrollment,
           medicaid_enrollment, chip_enrollment
    FROM staging_enrollment
    ON CONFLICT (state_code, report_month) DO UPDATE SET
        total_enrollment    = EXCLUDED.total_enrollment,
        medicaid_enrollment = EXCLUDED.medicaid_enrollment,
        chip_enrollment     = EXCLUDED.chip_enrollment,
        loaded_at           = now()
""")


def load(df: pd.DataFrame, engine: Engine) -> int:
    """Write df to staging, then upsert into enrollment. Returns rows inserted or updated."""
    with engine.begin() as conn:  # one transaction: all or nothing
        df.to_sql(STAGING_TABLE, conn, if_exists="replace", index=False, dtype=STAGING_TYPES)
        result = conn.execute(UPSERT)
        return result.rowcount
