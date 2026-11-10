"""Load: staging table + idempotent upsert in one transaction. Does I/O.

To write (plan section 6, load.py):
- UPSERT: INSERT INTO enrollment ... SELECT ... FROM staging_enrollment
  ON CONFLICT (state_code, report_month) DO UPDATE SET ..., loaded_at = now()
- load(df, engine): inside a single engine.begin() block, write df to
  staging_enrollment (if_exists="replace"), run UPSERT, return the row count
"""
