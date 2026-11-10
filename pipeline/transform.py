"""Transform: pure function, raw DataFrame in, clean DataFrame out. No I/O.

To write (plan section 6, transform.py):
- COLUMN_MAP: source column name -> our name (fill in from the real dataset)
- COUNT_COLS: total_enrollment, medicaid_enrollment, chip_enrollment
- transform(raw): normalise headers, rename and select, strip/uppercase state_code,
  parse report_month, strip commas and cast counts to Int64,
  drop duplicates on (state_code, report_month)
"""
