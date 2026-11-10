"""Shared fixtures.

To write (plan section 8):
- clean_df: transform() applied to tests/fixtures/sample_enrollment.csv
- engine: skip if DATABASE_URL is unset; otherwise create the engine, apply
  sql/schema.sql, TRUNCATE enrollment and pipeline_runs, yield, dispose
"""
